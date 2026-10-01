from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from shellix.cli import commands
from shellix.config.manager import ConfigManager, Settings
from shellix.ai.openrouter import AIRequestError

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(commands, "is_interactive", lambda: True)


def test_help_without_provider(monkeypatch):
    provider = Mock(side_effect=AssertionError("must not initialize"))
    monkeypatch.setattr(commands, "OpenRouterProvider", provider)
    for args in (["--help"], ["configure", "--help"]):
        result = runner.invoke(commands.app, args)
        assert result.exit_code == 0, result.output
    provider.assert_not_called()


def test_configure_and_keep_key(monkeypatch):
    provider = Mock()
    monkeypatch.setattr(commands, "OpenRouterProvider", provider)
    result = runner.invoke(commands.app, ["configure"], input="fake-secret\nvendor/model\n")
    assert result.exit_code == 0, result.output
    assert "fake-secret" not in result.output
    result = runner.invoke(commands.app, ["configure"], input="\nnew/model\n")
    assert result.exit_code == 0, result.output
    settings = ConfigManager().load()
    assert settings.api_key.get_secret_value() == "fake-secret"
    assert settings.model == "new/model"
    provider.assert_not_called()


def test_cancellation_preserves_settings(monkeypatch):
    manager = ConfigManager()
    manager.save(Settings(api_key="previous-secret", model="previous/model"))
    original = manager.path.read_bytes()
    result = runner.invoke(commands.app, ["configure"], input="replacement\n")
    assert result.exit_code == 130, result.output
    assert manager.path.read_bytes() == original
    assert "previous-secret" not in result.output
    assert "replacement" not in result.output


@pytest.mark.parametrize("input", ["\n", "key\n\n"])
def test_empty_setup_rejected(input):
    result = runner.invoke(commands.app, ["configure"], input=input)
    assert result.exit_code != 0
    assert ConfigManager().load() is None


def test_first_run_and_request_routing(monkeypatch):
    run = Mock()
    provider = Mock()
    monkeypatch.setattr(commands.ShellixCLI, "run", run)
    monkeypatch.setattr(commands, "OpenRouterProvider", provider)
    result = runner.invoke(commands.app, [], input="fake-key\nvendor/model\n")
    assert result.exit_code == 0, result.output
    run.assert_called_once_with(None)
    provider.assert_called_once_with(api_key="fake-key", model="vendor/model")
    run.reset_mock()
    result = runner.invoke(commands.app, ["list files"])
    assert result.exit_code == 0, result.output
    run.assert_called_once_with("list files")


def test_noninteractive_missing(monkeypatch):
    monkeypatch.setattr(commands, "is_interactive", lambda: False)
    for args in ([], ["list files"], ["configure"]):
        result = runner.invoke(commands.app, args)
        assert result.exit_code == 1
        assert "shellix configure" in result.output


def test_saved_config_ignores_environment(monkeypatch):
    ConfigManager().save(Settings(api_key="saved-key", model="saved/model"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "environment-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "environment/model")
    provider = Mock()
    monkeypatch.setattr(commands, "OpenRouterProvider", provider)
    monkeypatch.setattr(commands.ShellixCLI, "run", Mock())
    assert runner.invoke(commands.app, ["list files"]).exit_code == 0
    provider.assert_called_once_with(api_key="saved-key", model="saved/model")


def test_failed_request_never_executes(monkeypatch):
    ConfigManager().save(Settings(api_key="fake", model="vendor/model"))
    monkeypatch.setattr(commands.AIService, "generate_command", Mock(side_effect=AIRequestError("Request failed")))
    execute = Mock()
    monkeypatch.setattr(commands.CommandExecutor, "execute", execute)
    result = runner.invoke(commands.app, ["list files"])
    assert result.exit_code == 1
    assert "Request failed" in result.output
    execute.assert_not_called()


def test_request_named_run_is_not_reserved(monkeypatch):
    ConfigManager().save(Settings(api_key="fake", model="vendor/model"))
    run = Mock()
    monkeypatch.setattr(commands.ShellixCLI, "run", run)
    assert runner.invoke(commands.app, ["run"]).exit_code == 0
    run.assert_called_once_with("run")


def test_keyboard_cancellation_preserves_settings(monkeypatch):
    manager = ConfigManager()
    manager.save(Settings(api_key="previous", model="vendor/model"))
    previous = manager.path.read_bytes()
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(commands.typer, "prompt", interrupt)
    assert runner.invoke(commands.app, ["configure"]).exit_code == 130
    assert manager.path.read_bytes() == previous


@pytest.mark.parametrize("status, body", [
    (401, {}), (404, {}), (503, {}), (200, {}),
    (200, {"choices": [{"message": {"content": "not JSON"}}]}),
])
def test_provider_failures_never_execute(monkeypatch, status, body):
    import httpx
    ConfigManager().save(Settings(api_key="fake", model="vendor/model"))
    real_client = httpx.Client
    monkeypatch.setattr("shellix.ai.openrouter.httpx.Client", lambda **kwargs:
        real_client(transport=httpx.MockTransport(lambda req: httpx.Response(status, json=body)), **kwargs))
    execute = Mock()
    monkeypatch.setattr(commands.CommandExecutor, "execute", execute)
    assert runner.invoke(commands.app, ["list files"]).exit_code == 1
    execute.assert_not_called()


def test_entrypoint_does_not_load_project_dotenv(monkeypatch, tmp_path):
    from shellix import main as entrypoint
    import os
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fake-dotenv-secret\n")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(entrypoint, "app", Mock())
    entrypoint.main()
    assert "OPENROUTER_API_KEY" not in os.environ
