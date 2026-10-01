import json
import os

import pytest
from pydantic import ValidationError

from shellix.config.manager import ConfigManager, ConfigurationError, Settings


def test_user_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert ConfigManager().path == tmp_path / "shellix/config.json"
    monkeypatch.setenv("HOME", str(tmp_path))
    for value in ("", "relative"):
        monkeypatch.setenv("XDG_CONFIG_HOME", value)
        assert ConfigManager().path == tmp_path / ".config/shellix/config.json"
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert ConfigManager().path == tmp_path / ".config/shellix/config.json"


def test_roundtrip_permissions_and_secret_repr(tmp_path):
    manager = ConfigManager(tmp_path / "shellix/config.json")
    assert manager.load() is None
    settings = Settings(api_key="fake-secret", model="vendor/model")
    manager.save(settings)
    assert manager.load() == settings
    assert manager.path.stat().st_mode & 0o777 == 0o600
    assert manager.path.parent.stat().st_mode & 0o777 == 0o700
    assert "fake-secret" not in repr(settings)
    manager.path.chmod(0o644)
    manager.path.parent.chmod(0o755)
    manager.save(Settings(api_key="new-secret", model="other/model"))
    assert manager.load().model == "other/model"
    assert manager.path.stat().st_mode & 0o777 == 0o600
    assert manager.path.parent.stat().st_mode & 0o777 == 0o700


def test_atomic_failure_preserves_previous(monkeypatch, tmp_path):
    manager = ConfigManager(tmp_path / "shellix/config.json")
    previous = Settings(api_key="old", model="old/model")
    manager.save(previous)
    def fail(*args):
        raise OSError("failure")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(ConfigurationError):
        manager.save(Settings(api_key="new", model="new/model"))
    assert manager.load() == previous
    assert list(manager.path.parent.iterdir()) == [manager.path]


@pytest.mark.parametrize("data", [
    {"api_key": "", "model": "model"},
    {"api_key": "key", "model": "  "},
    {"api_key": "key", "model": "model", "provider": "nvidia"},
])
def test_reject_invalid(data):
    with pytest.raises(ValidationError):
        Settings(**data)


def test_invalid_file_does_not_expose_secret(tmp_path):
    manager = ConfigManager(tmp_path / "config.json")
    manager.path.write_text(json.dumps({"api_key": "private", "model": ""}))
    with pytest.raises(ConfigurationError) as error:
        manager.load()
    assert "private" not in str(error.value)
