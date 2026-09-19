from __future__ import annotations

import os
import platform

from shellix.core.models import TerminalContext


class SessionManager:
    def get_terminal_context(self) -> TerminalContext:
        """Build and return the current terminal context."""

        return TerminalContext(
            os=platform.system(),
            shell=os.environ.get("SHELL", "Unknown"),
            current_directory=os.getcwd(),
        )

    def get_current_directory(self) -> str:
        return os.getcwd()

    def get_shell(self) -> str:
        return os.environ.get("SHELL", "Unknown")

    def get_os(self) -> str:
        return platform.system()