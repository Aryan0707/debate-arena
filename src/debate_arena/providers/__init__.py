"""LLM provider abstractions for the debate arena."""

from debate_arena.providers.base import (
    Message,
    Provider,
    ProviderError,
    completion_to_text,
)
from debate_arena.providers.factory import (
    detect_provider,
    get_provider,
    list_providers,
)
from debate_arena.providers.stub import StubProvider

__all__ = [
    "Message",
    "OllamaProvider",
    "Provider",
    "ProviderError",
    "StubProvider",
    "anthropic",
    "completion_to_text",
    "detect_provider",
    "get_provider",
    "list_providers",
    "ollama",
    "openai",
    "openrouter",
    "stub",
]


# Lazy attribute-based access so missing optional deps don't break import.
def __getattr__(name: str):  # pragma: no cover
    if name == "AnthropicProvider":
        from debate_arena.providers.anthropic import AnthropicProvider

        return AnthropicProvider
    if name == "OpenAIProvider":
        from debate_arena.providers.openai import OpenAIProvider

        return OpenAIProvider
    if name == "OpenRouterProvider":
        from debate_arena.providers.openrouter import OpenRouterProvider

        return OpenRouterProvider
    if name == "OllamaProvider":
        from debate_arena.providers.ollama import OllamaProvider

        return OllamaProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
