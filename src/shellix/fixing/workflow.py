"""One request, one review, explicitly approved file writes. No command tools."""
from pathlib import Path
import subprocess
import tempfile

from shellix.ai.openrouter import AIRequestError
from shellix.fixing.project import FixError, Project, MAX_CONTEXT, MAX_FILE, diff, sensitive


class FixWorkflow:
    def __init__(self, ui, provider=None):
        self.ui = ui
        self.provider = provider

    def run(self, root: Path, problem: str, errors: str = '', undo: str | None = None):
        project = None
        try:
            project = Project(root)
            if undo:
                originals, edits = project.undo_edits(undo)
                diagnosis = f'Undo {undo}; restore the original contents and permissions.'
            else:
                if len(problem.encode()) + len(errors.encode()) > 16_000:
                    raise FixError('Problem and errors exceed the 16 KB input limit.')
                if sensitive(problem + '\n' + errors):
                    raise FixError('Remove potential credentials from the problem or errors before sending.')
                originals = project.collect()
                if not originals:
                    raise FixError('No eligible project files found.')
                manifest = '\n'.join(f'{p} ({len(s.content.encode())} bytes)' for p, s in originals.items())
                self.ui.show_info(f'Approved project: {project.root}\nOpenRouter will receive your problem, pasted errors, '
                                  f'and the UTF-8 contents of these files:\n{manifest}\n'
                                  'Other files are excluded. Do not include secrets in your problem or errors. '
                                  'No file contents are sent until you approve. Context is limited to 40 files / 128 KB.')
                if not self.ui.confirm_send():
                    self.ui.show_info('Permission denied. No AI request or file changes.')
                    return
                # Check after consent; do not silently send newer contents.
                for path, original in originals.items():
                    if project.read(path) != original:
                        raise FixError('Project changed before sending. Start a new review.')
                proposal = self.provider.generate_fix(problem=problem, errors=errors,
                                                      files={p: s.content for p, s in originals.items()})
                diagnosis = proposal.diagnosis
                edits = {}
                for edit in proposal.edits:
                    if edit.path not in originals or edit.path in edits:
                        raise FixError('AI proposed an unapproved or duplicate file. Nothing applied.')
                    if len(edit.content.encode()) > MAX_FILE or '\0' in edit.content or sensitive(edit.content):
                        raise FixError('AI proposed oversized, binary, or potentially sensitive content.')
                    edits[edit.path] = edit.content
                if sum(len(c.encode()) for c in edits.values()) > MAX_CONTEXT:
                    raise FixError('AI edits exceed the context limit.')
            while True:
                edits = {p: c for p, c in edits.items() if c != originals[p].content}
                if not edits:
                    self.ui.show_info('No file changes proposed.')
                    return
                patch = diff(originals, edits)
                action = self.ui.review_fix(diagnosis, list(edits), patch)
                if action == 'reject':
                    self.ui.show_info('Rejected. No file changes.')
                    return
                if action == 'vim':
                    path = self.ui.choose_file(list(edits))
                    if path in edits:
                        edits[path] = self.edit_in_vim(path, edits[path])
                    continue  # regenerate diff and require a fresh Apply decision
                if action != 'apply':
                    raise FixError('No explicit Apply approval received.')
                ident = project.apply(originals, edits)
                self.ui.show_success('Applied exactly these changes:\n' + patch +
                                     f'\nUndo: shellix fix --project {str(project.root)!r} --undo {ident}')
                self.run_check(project.root)
                return
        except (AIRequestError, FixError):
            raise
        except (OSError, UnicodeError, ValueError):
            raise FixError('Fix workflow failed safely. Check project access and the undo record if applying was interrupted.') from None
        finally:
            if project:
                project.close()

    def run_check(self, root: Path):
        from shellix.safety.validator import SafetyValidator
        from shellix.executor.executor import CommandExecutor
        command = self.ui.get_check_command()
        if not command:
            self.ui.show_info('No commands were run.')
            return
        safety = SafetyValidator().validate(command)
        self.ui.show_info(f'Shellix Safety: {safety.level.value}')
        for reason in safety.reasons:
            self.ui.show_info(reason)
        if not safety.allowed:
            self.ui.show_error('Command blocked by Shellix. Files remain applied; undo is available.')
            return
        # In fix mode even commands classified SAFE need separate approval.
        if self.ui.confirm_command(command=command, safety_level=safety.level.value):
            self.ui.show_execution_result(CommandExecutor().execute(command, cwd=str(root)))
        else:
            self.ui.show_info('Command cancelled. Files remain applied; undo is available.')

    @staticmethod
    def edit_in_vim(path: str, content: str) -> str:
        # Called only after the prompt-toolkit review application has exited and
        # restored the terminal. Vim inherits the real terminal; no shell or keys.
        with tempfile.TemporaryDirectory(prefix='shellix-review-') as directory:
            proposed = Path(directory) / Path(path).name
            proposed.write_text(content, encoding='utf-8')
            result = subprocess.run(['vim', '-N', '-u', 'NONE', '-i', 'NONE', '-n',
                                     '--cmd', 'set nomodeline', '--', str(proposed)])
            if result.returncode:
                raise FixError('Vim failed. No project files were changed.')
            if proposed.is_symlink() or proposed.stat().st_nlink != 1 or proposed.stat().st_size > MAX_FILE:
                raise FixError('Edited proposal is invalid or oversized.')
            updated = proposed.read_text(encoding='utf-8')
            if '\0' in updated or sensitive(updated):
                raise FixError('Edited proposal contains binary or potentially sensitive content.')
            return updated
