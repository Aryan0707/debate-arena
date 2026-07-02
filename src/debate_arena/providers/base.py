"""Provider base classes and shared types."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Message:
    """A single chat message."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class Completion:
    """The result of a single completion call."""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)


class ProviderError(RuntimeError):
    """Raised when a provider API call fails."""


class Provider(Protocol):
    """Protocol that all providers must implement."""

    name: str
    default_model: str

    def complete(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Completion: ...


def completion_to_text(completion: Completion) -> str:
    """Helper: pull just the text out of a completion."""
    return completion.content


def env_or(default: str, *keys: str) -> str:
    """Return the first non-empty env var among keys, else default."""
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return default
