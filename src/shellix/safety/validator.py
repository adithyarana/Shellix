from __future__ import annotations
import re
from shellix.core.models import SafetyLevel, SafetyResult


class SafetyValidator:
    CRITICAL_PATTERNS = [
        r"\brm\s+-rf\s+/",
        r"\brm\s+-rf\s+--no-preserve-root",
        r"\bmkfs(\.[a-z0-9]+)?\b",
        r"\bdd\s+.*\bof=/dev/",
        r"\b(shutdown|poweroff|halt)\b",
        r"\breboot\b",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\};:",
    ]

    HIGH_PATTERNS = [
        r"\brm\s+-rf\b",
        r"\brm\s+-r\b",
        r"\bsudo\s+",
        r"\bchmod\s+777\b",
        r"\bchown\s+-R\b",
        r"\bkill\s+-9\b",
        r"\bpkill\b",
        r"\biptables\b",
        r"\buserdel\b",
        r"\bgroupdel\b",
    ]

    MEDIUM_PATTERNS = [
        r"\brm\s+",
        r"\bmv\s+",
        r"\bcp\s+",
        r"\bchmod\s+",
        r"\bchown\s+",
        r"\bsystemctl\s+(start|stop|restart|enable|disable)\b",
        r"\bapt\s+(install|remove|purge)\b",
        r"\bapt-get\s+(install|remove|purge)\b",
        r"\bpip\s+install\b",
        r"\bnpm\s+(install|uninstall)\b",
    ]

    def validate(self, command: str) -> SafetyResult:
        normalized_command = command.strip()

        if not normalized_command:
            return SafetyResult(
                level=SafetyLevel.CRITICAL,
                allowed=False,
                requires_confirmation=False,
                reasons=["Empty command was provided."],
            )

        critical_reasons = self._match_patterns(
            normalized_command,
            self.CRITICAL_PATTERNS,
        )

        if critical_reasons:
            return SafetyResult(
                level=SafetyLevel.CRITICAL,
                allowed=False,
                requires_confirmation=False,
                reasons=critical_reasons,
            )

        high_reasons = self._match_patterns(
            normalized_command,
            self.HIGH_PATTERNS,
        )

        if high_reasons:
            return SafetyResult(
                level=SafetyLevel.HIGH,
                allowed=True,
                requires_confirmation=True,
                reasons=high_reasons,
            )

        medium_reasons = self._match_patterns(
            normalized_command,
            self.MEDIUM_PATTERNS,
        )

        if medium_reasons:
            return SafetyResult(
                level=SafetyLevel.MEDIUM,
                allowed=True,
                requires_confirmation=True,
                reasons=medium_reasons,
            )

        return SafetyResult(
            level=SafetyLevel.SAFE,
            allowed=True,
            requires_confirmation=False,
            reasons=["No known dangerous pattern detected."],
        )

    @staticmethod
    def _match_patterns(
        command: str,
        patterns: list[str],
    ) -> list[str]:
        reasons: list[str] = []

        for pattern in patterns:
            if re.search(pattern, command, flags=re.IGNORECASE):
                reasons.append(
                    f"Dangerous pattern detected: {pattern}"
                )

        return reasons