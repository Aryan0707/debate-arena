"""Configuration objects for the debate arena."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DebateConfig:
    """Configuration for a single debate run."""

    question: str
    personas: list[str] = field(
        default_factory=lambda: ["skeptic", "optimist", "engineer"]
    )
    rounds: int = 1
    moderator: str = "moderator"
    include_synthesis: bool = True
    model: str | None = None
    provider: str | None = None

    def __post_init__(self) -> None:
        if not self.question or not self.question.strip():
            raise ValueError("question must be a non-empty string")
        if self.rounds < 0:
            raise ValueError("rounds must be >= 0")
        if not self.personas:
            raise ValueError("at least one persona is required")
        # dedupe personas but preserve order
        seen: set[str] = set()
        unique: list[str] = []
        for p in self.personas:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        self.personas = unique
