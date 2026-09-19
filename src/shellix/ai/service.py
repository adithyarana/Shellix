from __future__ import annotations

from shellix.ai.provider import AIProvider
from shellix.core.models import AIResponse, TerminalContext


class AIService:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def generate_command(
        self,
        *,
        prompt: str,
        context: TerminalContext,
    ) -> AIResponse:
        """Generate a command from a natural-language request."""

        return self.provider.generate(
            prompt=prompt,
            context=context,
        )