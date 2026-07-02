"""Debate presets — pre-configured combinations of personas + settings.

A preset is a one-click "starting point" for common question types:
- product_decision: should we ship this?
- career_choice: should I take this job / leave this job?
- strategic_bet: should we make this big long-term move?
- etc.

Each preset auto-fills the question (with an editable example), the
persona selection, and the crossfire rounds. Users can still edit
any field after applying — it's a shortcut, not a constraint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PRESETS_FILE = Path(__file__).resolve().parent.parent.parent / "personas" / "presets.json"


@dataclass
class Preset:
    """A pre-configured debate starting point."""

    id: str
    name: str
    emoji: str
    description: str
    example_question: str
    personas: list[str]
    rounds: int
    color: str = "#64748b"  # fallback accent color


def load_presets(presets_file: Path | None = None) -> list[Preset]:
    """Load all presets from the JSON file."""
    path = presets_file or PRESETS_FILE
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [Preset(**preset) for preset in data.get("presets", [])]


def get_preset(preset_id: str, presets_file: Path | None = None) -> Preset | None:
    """Look up a single preset by id."""
    for preset in load_presets(presets_file):
        if preset.id == preset_id:
            return preset
    return None
