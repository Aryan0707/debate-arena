"""Persona loading and management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PERSONAS_DIR = Path(__file__).resolve().parent.parent.parent / "personas"


@dataclass
class Persona:
    """A debate persona: system prompt + sampling parameters."""

    id: str
    name: str
    description: str
    system_prompt: str
    temperature: float = 0.7

    def render_user_message(self, question: str, prior_turns: list[str] | None = None) -> str:
        """Build the user message for this persona's turn.

        On the opening turn, prior_turns is empty.
        On rebuttal turns, prior_turns contains other personas' statements from this round.
        """
        if not prior_turns:
            return (
                f"QUESTION: {question}\n\n"
                f"State your opening position in 150-300 words. "
                f"Be concrete. Use your persona's lens."
            )

        prior = "\n\n---\n\n".join(prior_turns)
        return (
            f"QUESTION: {question}\n\n"
            f"OTHER PERSONAS HAVE SAID (round {len(prior_turns)}):\n\n"
            f"{prior}\n\n"
            f"---"
            f"\n\nNow respond. You may rebut, refine, or even partially concede — "
            f"but you must engage with the strongest specific points made by "
            f"the others. Stay in character. 150-300 words."
        )


def load_persona(persona_id: str, personas_dir: Path | None = None) -> Persona:
    """Load a persona by id from a YAML file."""
    base = personas_dir or PERSONAS_DIR
    path = base / f"{persona_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"persona '{persona_id}' not found at {path}. "
            f"Available: {sorted(p.stem for p in base.glob('*.yaml'))}"
        )
    data = yaml.safe_load(path.read_text())
    return Persona(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        system_prompt=data["system_prompt"],
        temperature=float(data.get("temperature", 0.7)),
    )


def load_personas(persona_ids: list[str], personas_dir: Path | None = None) -> list[Persona]:
    """Load multiple personas in order."""
    return [load_persona(pid, personas_dir) for pid in persona_ids]
