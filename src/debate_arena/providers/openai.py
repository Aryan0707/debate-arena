"""OpenAI provider (GPT-4o, etc.) using the Chat Completions API over HTTP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from debate_arena.providers.base import (
    Completion,
    Message,
    ProviderError,
    env_or,
)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class OpenAIProvider:
    """OpenAI Chat Completions provider using direct HTTP calls."""

    name: str = "openai"
    default_model: str = DEFAULT_MODEL
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 60.0
    model: str | None = None  # accepted for factory compatibility

    def __post_init__(self) -> None:
        self.api_key = self.api_key or env_or("", "OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "OPENAI_API_KEY not set. "
                "Set it in your environment or use --provider stub for demo mode."
            )

    def _convert(self, messages: list[Message]) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Completion:
        model = model or self.default_model
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": self._convert(messages),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key or ''}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise ProviderError(f"OpenAI request failed: {e}") from e

        if resp.status_code >= 400:
            raise ProviderError(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"Unexpected OpenAI response shape: {data}") from e

        usage = data.get("usage", {})
        return Completion(
            content=text,
            model=data.get("model", model),
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        )
