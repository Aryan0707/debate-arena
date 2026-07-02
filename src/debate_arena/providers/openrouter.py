"""OpenRouter provider — same shape as OpenAI but routes to any model."""

from __future__ import annotations

from dataclasses import dataclass

from debate_arena.providers.base import (
    ProviderError,
    env_or,
)
from debate_arena.providers.openai import OpenAIProvider

OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"


@dataclass
class OpenRouterProvider(OpenAIProvider):
    """OpenRouter provider. Identical wire format to OpenAI Chat Completions."""

    name: str = "openrouter"
    default_model: str = DEFAULT_MODEL
    base_url: str = OPENROUTER_URL

    def __post_init__(self) -> None:
        self.api_key = self.api_key or env_or("", "OPENROUTER_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "OPENROUTER_API_KEY not set. "
                "Set it in your environment or use --provider stub for demo mode."
            )
