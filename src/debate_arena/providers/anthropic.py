"""Anthropic provider (Claude) using the Messages API over HTTP."""

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

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class AnthropicProvider:
    """Anthropic Claude provider using direct HTTP calls (no SDK required)."""

    name: str = "anthropic"
    default_model: str = DEFAULT_MODEL
    api_key: str | None = None
    timeout: float = 60.0
    model: str | None = None  # accepted for factory compatibility; per-call model wins

    def __post_init__(self) -> None:
        self.api_key = self.api_key or env_or("", "ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY not set. "
                "Set it in your environment or use --provider stub for demo mode."
            )

    def _convert(self, messages: list[Message]) -> tuple[str, list[dict[str, str]]]:
        """Split into system prompt + user/assistant turns (Anthropic format)."""
        system_parts: list[str] = []
        converted: list[dict[str, str]] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            else:
                converted.append({"role": m.role, "content": m.content})
        return "\n\n".join(system_parts), converted

    def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Completion:
        model = model or self.default_model
        system, msgs = self._convert(messages)

        if not msgs:
            raise ProviderError("Anthropic requires at least one user/assistant message")

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": msgs,
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise ProviderError(f"Anthropic request failed: {e}") from e

        if resp.status_code >= 400:
            raise ProviderError(f"Anthropic API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        content_blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        usage = data.get("usage", {})
        return Completion(
            content=text,
            model=data.get("model", model),
            usage={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
        )
