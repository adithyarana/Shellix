from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator


class ConfigurationError(Exception):
    """A configuration failure with a message safe to display."""


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "openrouter"
    api_key: SecretStr = Field(repr=False)
    model: str

    @field_validator("provider")
    @classmethod
    def supported_provider(cls, value: str) -> str:
        if value != "openrouter":
            raise ValueError("Only OpenRouter is supported")
        return value

    @field_validator("api_key", mode="before")
    @classmethod
    def valid_key(cls, value: object) -> str:
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not isinstance(value, str) or not value.strip():
            raise ValueError("API key is required")
        return value.strip()

    @field_validator("model")
    @classmethod
    def valid_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Model ID is required")
        return value.strip()


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        root = os.environ.get("XDG_CONFIG_HOME", "")
        base = Path(root) if root and Path(root).is_absolute() else Path.home() / ".config"
        self.path = path if path is not None else base / "shellix" / "config.json"

    def load(self) -> Settings | None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError:
            raise ConfigurationError("Cannot read settings. Check config file permissions.") from None
        try:
            return Settings.model_validate_json(raw)
        except (ValidationError, ValueError):
            # Validation errors may include the secret input; never display them.
            raise ConfigurationError("Invalid settings. Run shellix configure to replace them.") from None

    def save(self, settings: Settings) -> None:
        temporary: str | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.path.parent.chmod(0o700)
            fd, temporary = tempfile.mkstemp(prefix=".config-", dir=self.path.parent)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump({"provider": settings.provider,
                           "api_key": settings.api_key.get_secret_value(),
                           "model": settings.model}, stream)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise ConfigurationError("Cannot save settings. Check config directory permissions.") from None
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
