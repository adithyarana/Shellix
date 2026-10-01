# Shellix

Shellix converts natural-language requests into Linux shell commands using
OpenRouter. Requires Python 3.11 or newer and an OpenRouter API key.

## Install from this repository

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

For development and packaging checks, install `python -m pip install -e '.[dev]'`.
Build distributable artifacts with `python -m build`, then install the resulting
wheel with `python -m pip install dist/shellix_ai-0.1.0-py3-none-any.whl`.
The distribution name is `shellix-ai`; the Python import package and terminal
command remain `shellix`. The PyPI name `shellix` belongs to another distribution.
This release has not been published, and availability/ownership of `shellix-ai`
still needs confirmation. After publication under that name, install it with
`python -m pip install shellix-ai`. Until then, use the local installation commands
above.

## First launch

Run `shellix` in an interactive terminal. Shellix asks for an **OpenRouter-issued
API key** with hidden input, then an OpenRouter model ID. Copy the exact model ID
from your OpenRouter account/catalog. NVIDIA models offered through OpenRouter
are supported using their OpenRouter IDs; a direct NVIDIA API key is not accepted.
Setup saves the settings and opens the assistant. Setup does not make an API
request; credentials and model availability are checked when you submit a request.

```bash
shellix
shellix "list files"
shellix configure
shellix --help
```

Type `exit`, `quit`, or `:q` to leave interactive mode. `shellix configure` changes
the key and model without starting the assistant. Leave the key blank to keep
an existing key; it is never displayed. The existing model is the prompt default.
Ctrl-C or EOF before saving preserves previous settings.

## Configuration

The sole source of API key/model configuration is the per-user JSON file at
`$XDG_CONFIG_HOME/shellix/config.json`, or `~/.config/shellix/config.json` when
XDG_CONFIG_HOME is unset, empty, or relative. The provider is always `openrouter`.
Shellix does not load project `.env` files and ignores `OPENROUTER_API_KEY` and
`OPENROUTER_MODEL` environment variables. There are no implicit model defaults.

The Shellix directory has permissions `0700`; the file has permissions `0600`.
The key is stored in plaintext accessible to your Linux account. Writes use a
private temporary file and atomic replacement. Never commit this file.

Missing configuration in noninteractive use exits with instructions to run
`shellix configure` in a terminal. Invalid configuration can be replaced with that
command. Network, authentication, model/request, and response-validation errors
stop the request before command execution. Check your account for credits and
model availability. AI requests send your prompt, OS, shell, and working directory
to OpenRouter; they may incur charges according to your account and model.

Shellix uses its existing local command-pattern safety validator: blocked commands
are rejected, commands requiring confirmation prompt first, and commands classified
safe execute automatically. This classification is not a complete shell security
analysis; review what you ask Shellix to do.

## Release checks

```bash
python -m pytest
python -m build
python -m twine check dist/*
```

Before publishing, confirm PyPI project-name availability/ownership, review the
release metadata and artifacts, test the release on supported Python versions,
and configure publishing credentials or trusted publishing. Publication is a
separate step; this repository workflow does not upload anything.
