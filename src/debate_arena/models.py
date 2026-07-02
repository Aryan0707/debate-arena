"""Data models for debate results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PersonaTurn:
    """A single turn in a debate by a single persona."""

    persona: str
    round: int
    phase: str  # "opening", "rebuttal", "synthesis"
    content: str
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class DebateResult:
    """The full result of a debate run."""

    question: str
    transcript: list[PersonaTurn]
    synthesis: str | None
    config: dict
    total_usage: dict[str, int] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Render the full debate as a markdown document."""
        lines: list[str] = []
        lines.append(f"# Debate: {self.question}\n")

        # Group turns by round/phase for readability
        for turn in self.transcript:
            header = (
                f"## {turn.persona} — Round {turn.round} ({turn.phase})"
                if turn.phase != "synthesis"
                else f"## {turn.persona} (synthesis)"
            )
            lines.append(header)
            lines.append("")
            lines.append(turn.content)
            lines.append("")

        if self.synthesis:
            lines.append("---\n")
            lines.append("# 🏁 Final Synthesis\n")
            lines.append(self.synthesis)
            lines.append("")

        return "\n".join(lines)
