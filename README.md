<h1 align="center">⚡ Shellix AI</h1>

<p align="center">
  Turn plain-language requests into Linux shell commands with OpenRouter.
</p>

<p align="center">
  <a href="https://pypi.org/project/shellix-ai/"><img src="https://img.shields.io/pypi/v/shellix-ai?color=2563eb" alt="PyPI version"></a>
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/Python-3.11%2B-2563eb" alt="Requires Python 3.11 or newer"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-16a34a" alt="MIT license"></a>
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#setup">Setup</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#troubleshooting">Troubleshooting</a>
</p>

Shellix AI is a terminal assistant for Linux. Describe a task, and it asks an
OpenRouter model for a command and explanation, checks the command locally,
and displays the result of execution.

- **Plain-language requests** in an interactive session or a single command.
- **Your OpenRouter key and model**, with hidden key input and saved user settings.
- **Local safety checks** that block recognized critical patterns and ask for
  confirmation on recognized medium/high-risk commands.
- **Clear request errors** that stop failed AI requests before execution.

**Commands classified as safe execute automatically.** The checks are pattern
based, so use requests you understand and read the [safety limitations](#settings-and-safety).

<a id="installation"></a>

## 🚀 Install and start

These steps are for a Linux terminal using Bash or Zsh. You need Python 3.11 or
newer, internet access, and an OpenRouter account.

1. **Check your Python version.**

   ```bash
   python3 --version
   ```

   The result must be **3.11 or newer**. If Python is missing or older, install a
   supported version using your Linux distribution's instructions.

2. **Create and activate a virtual environment.**

   A virtual environment keeps Shellix's dependencies separate from system Python.
   Run this once to create a dedicated environment in your home directory:

   ```bash
   python3 -m venv ~/.venvs/shellix
   source ~/.venvs/shellix/bin/activate
   ```

   After activation, `python` and `pip` refer to this environment.

3. **Install the package.**

   ```bash
   python -m pip install shellix-ai
   ```

   The [PyPI distribution](https://pypi.org/project/shellix-ai/) is named
   **`shellix-ai`**. The terminal command and Python import package are both
   **`shellix`**. If a release is not yet available on PyPI, use the source
   installation in [Development](#development).

4. **Start Shellix.**

   ```bash
   shellix
   ```

   On your first launch, complete the [OpenRouter setup](#setup) below. Shellix
   then opens its interactive prompt.

5. **Activate the environment again in each new terminal.**

   You only need to create the environment and install once. In a new terminal:

   ```bash
   source ~/.venvs/shellix/bin/activate
   shellix
   ```

   Run `deactivate` when you want to leave the virtual environment.

<a id="setup"></a>

## 🔑 First-run setup

Shellix supports **OpenRouter only**. The first interactive launch asks for two
values:

1. Create an API key at [OpenRouter Keys](https://openrouter.ai/keys).
2. Paste it at **`OpenRouter API key:`** and press Enter. Input is hidden; no
   characters or asterisks appear as you type or paste.
3. Copy an exact model ID from the [OpenRouter model catalog](https://openrouter.ai/models)
   and enter it at **`OpenRouter model ID:`**. Use the ID, not the model's display
   name. Both the key and model ID are required.

NVIDIA models offered through OpenRouter still require an **OpenRouter-issued
key**. Shellix does not connect directly to NVIDIA's API.

Setup saves your settings without making an AI request. Your key and model are
checked when you submit a request. Press Ctrl-C to cancel setup.

<a id="usage"></a>

## 💬 Usage

Start an interactive session:

```bash
shellix
```

At `shellix ❯`, type a request such as `list files`. Exit with `exit`, `quit`,
`:q`, or Ctrl-C.

For one request, put the whole sentence in quotes:

```bash
shellix "list files"
```

Shellix runs in your current working directory. Commands execute in a subprocess;
Shellix is an assistant rather than a replacement for your shell, and a generated
`cd` command does not change your terminal's directory.

### Review a code fix (source version)

```bash
shellix fix "Handle empty input without crashing" --project /path/to/project
```

Omit `--project` to select a directory interactively. Omit the problem to enter it
at a prompt. Paste terminal errors at `error>` and finish with a line containing
only `.` (use `.` immediately to skip errors). Fix mode requires an interactive
terminal and uses the saved OpenRouter settings.

1. Shellix lists the exact eligible filenames and byte sizes. Your problem,
   pasted errors, and these files' full UTF-8 contents are sent to OpenRouter
   **only after you answer yes** to the context permission prompt. Answering no
   makes no API request. Remove sensitive data before approving a request.
2. One AI request returns a diagnosis and structured full-file replacements.
   The model receives no file-writing or execution tools. Invalid proposals,
   duplicate paths, and paths outside the approved context are rejected.
3. Review the diagnosis, affected files, and unified diff. Terminals at least
   100 columns wide show conversation/diagnosis beside the diff; narrower
   terminals stack the panes. Use Tab to switch panes and arrow/page keys to
   scroll. **Ctrl-A applies, Ctrl-R rejects, Ctrl-V opens Vim**, and Ctrl-C rejects.
4. Vim edits a temporary proposed file, never the project original. Select a file
   number; exit Vim normally to return. Shellix recalculates the diff and requires
   a fresh Apply decision. Vim uses clean settings, no swap/viminfo, and disabled
   modelines; no editor keystrokes are automated.
5. Apply rechecks original contents, permissions, and file identity/timestamps,
   saves a durable private undo record, then atomically replaces each approved
   file while preserving its permissions. The final output prints exactly the
   applied diff and an undo command.
6. Optionally enter one test/check command after applying. It passes through the
   existing safety validator and requires **separate confirmation even if SAFE**.
   It runs in the selected project, with the existing timeout. There are no
   automatic tests, dependency installations, retries, or further fix requests.

To review and undo an applied change, use the printed ID:

```bash
shellix fix --project /path/to/project --undo <id>
```

Undo is local, needs no API key/request, shows a diff, and requires Apply approval.
It refuses to overwrite subsequent changes. Original/replacement contents are
stored in `.shellix-undo/<id>.json` (directory `0700`, files `0600`), not in logs.
Keep that directory private and out of version control; records are retained
until you manually remove them. Interrupted applies retain the record and attempt
rollback; undo can restore files that were applied before an interruption.

**First-version limits.** Only existing eligible files can be edited: no creation,
deletion, renaming, or permission changes. Context includes at most 40 files,
128 KB total, 32 KB per file, and 16 KB of problem/errors; scanning stops after
2,000 entries. Selection is deterministic and may omit relevant files in large
projects; the model should return no edits if context is insufficient. Git must
be installed: its local ignore matcher handles nested `.gitignore` rules and
negations even outside repositories; repository/global exclusions also apply.
Internal Git calls only initialize temporary ignore metadata and check ignores.

Shellix excludes ignored files, symlinks, hard-linked files, binary/non-UTF-8
files, `.env*`, common credentials/key files, virtual environments, dependency
folders, build outputs, and common caches. Directory traversal uses no-follow
file descriptors to block symlink escapes. Filename/content credential detection
is conservative and heuristic; it cannot identify every secret. Review the file
list before sharing. Errors and file contents are treated as untrusted model data;
terminal controls are shown as escaped text. Prompt-injection defenses do not
make model suggestions trustworthy: read the diff before approval.

Each replacement is atomic, but a multi-file apply is not a filesystem-wide
transaction. Avoid concurrent writers during review/apply; there remains a small
race between the final stale check and atomic replacement. Permissions are
preserved, but ownership, ACLs, extended attributes, and original inode identity
are not preserved. User-approved check commands inherit the existing validator's
limitations and are not sandboxed to the project. This is a single review cycle,
not an autonomous coding agent.

**UI choice.** This version retains Rich for normal readable CLI output and
prompt-toolkit for a scrollable review screen. Textual supports
[horizontal/vertical layouts](https://textual.textualize.io/guide/layout/) and
[terminal suspension](https://textual.textualize.io/guide/app/#suspending), making
it a candidate for a richer persistent interface. Migrating would introduce a
new dependency and event loop for this focused workflow; prompt-toolkit already
supports [full-screen applications](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html).
Vim runs after the review application exits and restores the terminal. Text and
borders use terminal defaults for dark/light themes; status prefixes have text
labels with optional standard terminal red/green accents, never color alone.

### Example session

*Illustrative excerpt after setup, with the startup banner omitted. The command,
explanation, risk estimate, and file listing depend on your model and directory.*

```text
shellix ❯ list files
ℹ Thinking...

Suggested command:
╭──────────────────╮
│ ls               │
╰──────────────────╯
Explanation: List files in the current directory.
AI Risk: LOW

ℹ Shellix Safety: SAFE
ℹ No known dangerous pattern detected.
ℹ Command is considered safe.
ℹ Executing command...

✓ Command completed successfully (exit code 0).

Output:
README.md  src  tests
shellix ❯ exit
Goodbye! 👋
```

### Command reference

| Command | What it does |
| --- | --- |
| `shellix` | Start an interactive session; offer setup if settings are missing. |
| `shellix "list files"` | Process one request, then exit. |
| `shellix fix [problem] --project PATH` | Propose and review existing-file edits with explicit sharing/apply approval. |
| `shellix fix --project PATH --undo ID` | Review a local undo without an AI request. |
| `shellix configure` | Change the saved OpenRouter key and model. |
| `shellix --help` | Show CLI help without starting the AI provider. |
| `shellix --version` | Print `Shellix AI <version>` from the installed package and exit without setup or AI initialization. |
| `shellix configure --help` | Show help for configuration. |

### Change your key or model

```bash
shellix configure
```

When settings already exist, **leave the key input blank to keep the existing
key**. Shellix never displays it. Enter a new model ID, or press Enter to keep
its displayed default. Ctrl-C or end-of-input before saving preserves your
previous settings.

### Upgrade

Activate your Shellix environment first, then run:

```bash
python -m pip install --upgrade shellix-ai
```

<a id="troubleshooting"></a>

## 🛠 Troubleshooting

| Problem | What to try |
| --- | --- |
| `shellix: command not found` | Run `source ~/.venvs/shellix/bin/activate`. Ensure you installed into that environment. |
| Python is too old / no matching distribution | Check `python --version` for 3.11+. Check the [PyPI project](https://pypi.org/project/shellix-ai/) for an available release; otherwise install from source below. |
| `venv` or `ensurepip` is missing | Install your Linux distribution's Python venv support, then repeat environment creation. |
| Missing configuration in a script or pipe | Run `shellix configure` in an interactive terminal first. Setup requires a terminal; scripts can then submit a quoted request. |
| Authentication failed | Run `shellix configure` and enter a valid **OpenRouter** key. |
| Request or model ID rejected | Copy an available model's exact ID from OpenRouter and update it with `shellix configure`. |
| Insufficient credits / rate limit | Check your OpenRouter account balance, or wait and retry after a rate limit. |
| Cannot reach OpenRouter | Check your internet connection and retry. |
| Invalid model response | No command was executed. Retry, or choose another model with `shellix configure`. |
| Cannot read/save settings | Check ownership and permissions of your user config directory. Replace invalid settings with `shellix configure`. |

<a id="settings-and-safety"></a>

## Settings, privacy, and safety

**Local storage.** Settings are saved at `$XDG_CONFIG_HOME/shellix/config.json`.
If `XDG_CONFIG_HOME` is unset, empty, or relative, the location is
`~/.config/shellix/config.json`. Writes are atomic. The Shellix directory is
created/set to `0700` and the settings file to `0600`.

**Key protection.** The key is stored in plaintext, protected by Linux file
permissions rather than encryption. Keep the file private and out of version
control. Saved settings are the sole source of key/model configuration: Shellix
does not load project `.env` files or use `OPENROUTER_API_KEY` or
`OPENROUTER_MODEL` environment variables.

**Requests and costs.** Each AI request sends your request text, operating system,
shell, and working-directory path to OpenRouter. Requests may incur API costs;
check the selected model's pricing in the [OpenRouter catalog](https://openrouter.ai/models)
and your account before use.

**Safety limitations.** Shellix's local validator uses known command patterns;
it is not a sandbox or a complete security analysis. Recognized critical commands
are blocked; medium/high-risk commands require confirmation; commands classified
safe run automatically. The local validator controls these decisions, rather
than the model's risk estimate. AI can make mistakes, and dangerous shell
expressions may escape the checks. Failed AI requests do not execute commands.

<a id="development"></a>

## Development

From the repository root, create a separate environment and install the development
extras:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

This also installs Shellix from local source, so you can run `shellix` without a
published PyPI release. Run the tests and build checks with:

```bash
python -m pytest
python -m build
python -m twine check dist/*
```

AI tests use mocked requests and dummy credentials; they do not require an API
key or paid requests. Building creates a wheel and source archive in `dist/`.
Build checks do not publish the package.

## License

Shellix AI is released under the [MIT License](LICENSE).
