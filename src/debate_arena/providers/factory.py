"""Auto-detect which provider to use based on env vars."""

from __future__ import annotations

import os

from debate_arena.providers.base import Provider
from debate_arena.providers.stub import StubProvider


def detect_provider(name: str | None = None) -> str:
    """Detect the provider from a name hint and env vars.

    Priority:
    1. Explicit `name` argument
    2. DEBATE_PROVIDER env var
    3. First non-empty of: ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY
    4. "stub" (demo mode)
    """
    if name:
        return name.lower()
    env = os.environ.get("DEBATE_PROVIDER", "").lower()
    if env:
        return env
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "stub"


def get_provider(name: str | None = None, *, model: str | None = None) -> Provider:
    """Construct a provider by name. Falls back to stub if API key is missing."""
    target = detect_provider(name)

    if target == "anthropic":
        from debate_arena.providers.anthropic import AnthropicProvider
        return AnthropicProvider(model=model)
    if target == "openai":
        from debate_arena.providers.openai import OpenAIProvider
        return OpenAIProvider(model=model)
    if target == "openrouter":
        from debate_arena.providers.openrouter import OpenRouterProvider
        return OpenRouterProvider(model=model)
    if target == "stub":
        return StubProvider()
    raise ValueError(
        f"unknown provider: {target!r}. "
        f"Choose one of: anthropic, openai, openrouter, stub"
    )


def list_providers() -> list[str]:
    return ["anthropic", "openai", "openrouter", "stub"]


# Convenience aliases mirroring common usage.
anthropic = "anthropic"
openai = "openai"
openrouter = "openrouter"
stub = "stub"
