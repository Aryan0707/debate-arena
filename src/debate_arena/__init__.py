"""Multi-Claude Debate Arena: multi-agent AI debate with personas."""

from debate_arena.arena import DebateArena
from debate_arena.config import DebateConfig
from debate_arena.models import DebateResult, PersonaTurn
from debate_arena.personas import Persona, load_persona, load_personas
from debate_arena.providers import (
    AnthropicProvider,
    OpenAIProvider,
    OpenRouterProvider,
    Provider,
    StubProvider,
    get_provider,
)

__version__ = "0.1.0"

__all__ = [
    "AnthropicProvider",
    "DebateArena",
    "DebateConfig",
    "DebateResult",
    "OpenAIProvider",
    "OpenRouterProvider",
    "Persona",
    "PersonaTurn",
    "Provider",
    "StubProvider",
    "get_provider",
    "load_persona",
    "load_personas",
]
