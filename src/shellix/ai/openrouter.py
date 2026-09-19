from __future__ import annotations

import json
import os

import httpx

from shellix.ai.provider import AIProvider
from shellix.core.models import AIResponse, TerminalContext


class OpenRouterProvider(AIProvider):
    """AI provider implementation using OpenRouter."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv(
            "OPENROUTER_MODEL",
            "openai/gpt-4o-mini",
        )
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured."
            )

    def generate(
        self,
        *,
        prompt: str,
        context: TerminalContext,
    ) -> AIResponse:
        """Generate a command suggestion using OpenRouter."""

        system_prompt = self._build_system_prompt(context)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

        content = data["choices"][0]["message"]["content"]

        return self._parse_response(content)

    @staticmethod
    def _build_system_prompt(
        context: TerminalContext,
    ) -> str:
        """Build the system prompt sent to the AI."""

        return f"""
You are Shellix, an AI assistant for the Linux terminal.

Your job is to convert the user's natural-language request
into a Linux shell command.

Current terminal environment:

Operating System: {context.os}
Shell: {context.shell}
Current Directory: {context.current_directory}

Rules:

1. Generate commands compatible with the current environment.
2. Prefer simple and standard Linux commands.
3. Never invent files, directories, or system state.
4. Do not execute commands yourself.
5. Return only valid JSON.
6. The JSON must contain exactly these fields:

{{
    "command": "string",
    "explanation": "string",
    "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
    "requires_confirmation": true | false
}}

The command should perform the user's requested operation.
"""

    @staticmethod
    def _parse_response(content: str) -> AIResponse:
        """Parse and validate the AI response."""

        cleaned_content = content.strip()

        if cleaned_content.startswith("```"):
            cleaned_content = (
                cleaned_content
                .replace("```json", "", 1)
                .replace("```", "")
                .strip()
            )

        data = json.loads(cleaned_content)

        return AIResponse.model_validate(data)