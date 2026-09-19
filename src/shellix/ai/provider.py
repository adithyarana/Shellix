from __future__ import annotations
from abc import ABC, abstractmethod
from shellix.core.models import AIResponse, TerminalContext


class AIProvider(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        prompt: str,
        context: TerminalContext,
    ) -> AIResponse:
        """Generate a structured response from the AI."""

        raise NotImplementedError