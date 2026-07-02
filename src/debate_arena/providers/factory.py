"""Provider factory + auto-detection."""

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
    4. If ollama server is reachable, "ollama"
    5. "stub" (demo mode)
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
    if _ollama_reachable():
        return "ollama"
    return "stub"


def _ollama_reachable() -> bool:
    """Quick check: is an Ollama server running locally?"""
    import socket
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    # Parse host:port from the URL
    try:
        without_scheme = host.split("://", 1)[1]
        host_part, _, port_part = without_scheme.partition(":")
        port = int(port_part.split("/", 1)[0] or "11434")
    except (ValueError, IndexError):
        return False
    try:
        with socket.create_connection((host_part, port), timeout=0.5):
            return True
    except OSError:
        return False


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
    if target == "ollama":
        from debate_arena.providers.ollama import OllamaProvider
        return OllamaProvider(model=model)
    if target == "stub":
        return StubProvider()
    raise ValueError(
        f"unknown provider: {target!r}. "
        f"Choose one of: anthropic, openai, openrouter, ollama, stub"
    )


def list_providers() -> list[str]:
    return ["anthropic", "openai", "openrouter", "ollama", "stub"]


# Convenience aliases mirroring common usage.
anthropic = "anthropic"
openai = "openai"
openrouter = "openrouter"
ollama = "ollama"
stub = "stub"
