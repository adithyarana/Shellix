"""Bounded, no-follow project access and durable undo for existing text files."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import difflib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
import subprocess
import tempfile
import uuid

MAX_FILE = 32_000
MAX_CONTEXT = 128_000
MAX_FILES = 40
BLOCKED = {'.git', '.hg', '.svn', '.shellix-undo', '.venv', 'venv', 'env',
           'node_modules', 'vendor', 'dist', 'build', 'target', '__pycache__',
           '.pytest_cache', '.mypy_cache', '.tox', '.aws', '.ssh', '.codex', '.agents',
           '.kube', '.azure', '.docker', '.gnupg', '.npmrc', '.netrc', '.pypirc',
           '.git-credentials', '.htpasswd', '.cache', '.next', '.nuxt', 'site-packages',
           'coverage', '.coverage', '.DS_Store'}
SECRET = re.compile(r'(secret|credential|password|token|api[_-]?key|id_rsa|id_ed25519)', re.I)


class FixError(Exception):
    """Safe-to-display workflow failure."""


def allowed(path: str) -> bool:
    p = PurePosixPath(path)
    return (bool(path) and not p.is_absolute() and str(p) == path
            and all(x not in {'.', '..'} and x not in BLOCKED
                    and not x.lower().startswith(('.env', '.shellix-')) and not SECRET.search(x)
                    and not any(ord(c) < 32 or 127 <= ord(c) < 160 or unicodedata.category(c) == 'Cf' for c in x)
                    for x in p.parts)
            and p.suffix.lower() not in {'.pem', '.key', '.p12', '.pfx', '.keystore', '.db', '.sqlite', '.sqlite3', '.pyc'})


def sensitive(text: str) -> bool:
    return bool(re.search(
        r'-----BEGIN .*PRIVATE KEY|\b(?:sk-or-v1-|AKIA|ghp_|github_pat_)[A-Za-z0-9]|'
        r'(?im:^\s*[\"\']?(?:[\w-]*(?:secret|password|token)|api[_-]?key|'
        r'aws_access_key_id)[\"\']?\s*[:=]\s*\S+)', text
    ))


@dataclass(frozen=True)
class Snapshot:
    content: str
    mode: int
    identity: tuple[int, int, int, int]


class Project:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise FixError('Select a project directory.')
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.ignore_dir = tempfile.TemporaryDirectory(prefix='shellix-ignore-')
        try:
            result = subprocess.run(['git', 'init', '--bare', '--quiet', self.ignore_dir.name],
                                    capture_output=True)
        except OSError:
            self.close()
            raise FixError('Git is required to evaluate ignore rules safely.') from None
        if result.returncode:
            self.close()
            raise FixError('Git is required to evaluate ignore rules safely.')

    def close(self):
        os.close(self.fd)
        self.ignore_dir.cleanup()

    def ignored(self, path: str) -> bool:
        # Git's actual wildmatch semantics, including nested rules and negations.
        result = subprocess.run(['git', '-c', 'core.bare=false',
                                 '--git-dir', self.ignore_dir.name, '--work-tree', str(self.root),
                                 'check-ignore', '--no-index', '--quiet', '--', path],
                                cwd=self.root, capture_output=True)
        if result.returncode not in {0, 1}:
            raise FixError('Could not evaluate project ignore rules.')
        # Also honor the real repository's info/exclude and global excludes.
        actual = subprocess.run(['git', 'check-ignore', '--no-index', '--quiet', '--', path],
                                cwd=self.root, capture_output=True)
        return result.returncode == 0 or actual.returncode == 0

    def verify_root(self):
        current = os.stat(self.root, follow_symlinks=False)
        opened = os.fstat(self.fd)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise FixError('Approved project directory has changed.')

    @contextmanager
    def parent(self, path: str, *, internal=False):
        self.verify_root()
        if not internal and (not allowed(path) or self.ignored(path)):
            raise FixError('A proposed path is outside the approved file policy.')
        parts = PurePosixPath(path).parts
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = new
            yield fd, parts[-1]
        finally:
            os.close(fd)

    def read(self, path: str) -> Snapshot:
        with self.parent(path) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(fd, 'rb') as stream:
                st = os.fstat(stream.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > MAX_FILE:
                    raise FixError('Only small regular text files without hard links are supported.')
                data = stream.read(MAX_FILE + 1)
                if len(data) > MAX_FILE or b'\0' in data:
                    raise FixError('Binary or oversized file excluded.')
                content = data.decode('utf-8')
                if any(ord(c) < 32 and c not in '\n\r\t' for c in content):
                    raise FixError('Binary content excluded.')
                if sensitive(content):
                    raise FixError('Potential sensitive content excluded.')
                return Snapshot(content, stat.S_IMODE(st.st_mode),
                                (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_ctime_ns))

    def collect(self) -> dict[str, Snapshot]:
        files = {}
        size = 0
        scanned = 0
        for directory, dirs, names in os.walk(self.root, followlinks=False):
            if scanned >= 2000 or len(files) >= MAX_FILES or size >= MAX_CONTEXT:
                break
            scanned += 1
            dirs[:] = sorted(d for d in dirs if allowed((Path(directory) / d).relative_to(self.root).as_posix())
                             and not (Path(directory) / d).is_symlink()
                             and not self.ignored((Path(directory) / d).relative_to(self.root).as_posix() + '/'))
            for name in sorted(names):
                scanned += 1
                if scanned > 2000:
                    break
                path = (Path(directory) / name).relative_to(self.root).as_posix()
                try:
                    original = self.read(path)
                except (FixError, OSError, UnicodeError):
                    continue
                length = len(original.content.encode())
                if len(files) < MAX_FILES and size + length <= MAX_CONTEXT:
                    files[path] = original
                    size += length
        return files

    def replace(self, path: str, content: str, expected: Snapshot):
        if self.read(path) != expected:
            raise FixError(f'Stale file: {path}. No overwrite permitted.')
        with self.parent(path) as (parent, name):
            temp = '.shellix-' + uuid.uuid4().hex
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(content.encode())
                    os.fchmod(stream.fileno(), expected.mode)
                    stream.flush()
                    os.fsync(stream.fileno())
                if self.read(path) != expected:
                    raise FixError(f'Stale file: {path}. No overwrite permitted.')
                os.replace(temp, name, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                try:
                    os.unlink(temp, dir_fd=parent)
                except FileNotFoundError:
                    pass

    def save_record(self, record: dict) -> str:
        ident = uuid.uuid4().hex
        try:
            os.mkdir('.shellix-undo', 0o700, dir_fd=self.fd)
        except FileExistsError:
            pass
        with self.parent('.shellix-undo/' + ident + '.json', internal=True) as (parent, name):
            os.fchmod(parent, 0o700)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            with os.fdopen(fd, 'w') as stream:
                json.dump(record, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(parent)
        os.fsync(self.fd)
        return ident

    def apply(self, originals: dict[str, Snapshot], edits: dict[str, str]) -> str:
        if len(edits) > MAX_FILES or sum(len(c.encode()) for c in edits.values()) > MAX_CONTEXT:
            raise FixError('Edits exceed file or context limits.')
        for content in edits.values():
            if len(content.encode()) > MAX_FILE or '\0' in content or sensitive(content):
                raise FixError('Invalid or potentially sensitive replacement content.')
        for path in edits:
            if path not in originals or self.read(path) != originals[path]:
                raise FixError(f'Stale or unapproved file: {path}. Nothing applied.')
        record = {path: {'before': originals[path].content, 'after': content,
                         'mode': originals[path].mode} for path, content in edits.items()}
        ident = self.save_record(record)  # durable before any mutation
        applied = []
        try:
            for path, content in edits.items():
                self.replace(path, content, originals[path])
                applied.append(path)
        except (OSError, FixError, KeyboardInterrupt):
            # Durable record remains available even if rollback is interrupted.
            for path in reversed(applied):
                current = self.read(path)
                if current.content == edits[path]:
                    self.replace(path, originals[path].content, current)
            raise FixError(f'Apply interrupted; undo record {ident} retained. Check files before continuing.') from None
        return ident

    def undo_edits(self, ident: str):
        if not re.fullmatch('[0-9a-f]{32}', ident):
            raise FixError('Invalid undo ID.')
        with self.parent('.shellix-undo/' + ident + '.json', internal=True) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
            with os.fdopen(fd) as stream:
                record = json.loads(stream.read(2 * MAX_CONTEXT + 100_000))
        originals, edits = {}, {}
        for path, item in record.items():
            current = self.read(path)
            if current.content == item['before'] and current.mode == item['mode']:
                continue  # already undone, or not applied after interruption
            if current.content != item['after'] or current.mode != item['mode']:
                raise FixError(f'Cannot undo changed file: {path}. Nothing applied.')
            originals[path] = current
            edits[path] = item['before']
        return originals, edits


def diff(originals: dict[str, Snapshot], edits: dict[str, str]) -> str:
    chunks = []
    for path, content in edits.items():
        lines = difflib.unified_diff(originals[path].content.splitlines(keepends=True),
                                     content.splitlines(keepends=True),
                                     fromfile='a/' + path, tofile='b/' + path)
        for line in lines:
            chunks.append(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n')
    return ''.join(chunks)
