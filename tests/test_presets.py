"""Tests for the preset (quick-start) feature."""

from __future__ import annotations

from pathlib import Path

from debate_arena.presets import get_preset, load_presets


PRESETS_FILE = Path(__file__).resolve().parent.parent / "personas" / "presets.json"


def test_presets_file_exists():
    assert PRESETS_FILE.exists(), f"presets.json not found at {PRESETS_FILE}"


def test_load_presets_returns_list():
    presets = load_presets()
    assert isinstance(presets, list)
    assert len(presets) >= 5, "should have at least 5 presets for variety"


def test_presets_have_required_fields():
    for preset in load_presets():
        assert preset.id, "preset must have an id"
        assert preset.name, "preset must have a name"
        assert preset.emoji, "preset must have an emoji"
        assert preset.description, "preset must have a description"
        assert preset.example_question, "preset must have an example question"
        assert isinstance(preset.personas, list)
        assert len(preset.personas) >= 2, "preset must use at least 2 personas"
        assert isinstance(preset.rounds, int)
        assert 0 <= preset.rounds <= 3, "rounds should be in 0-3 range"


def test_preset_ids_are_unique():
    presets = load_presets()
    ids = [p.id for p in presets]
    assert len(ids) == len(set(ids)), f"duplicate preset ids: {ids}"


def test_preset_personas_exist():
    """All personas referenced in presets must exist in the personas/ dir."""
    from debate_arena.personas import PERSONAS_DIR
    available = {p.stem for p in PERSONAS_DIR.glob("*.yaml")}
    for preset in load_presets():
        for persona in preset.personas:
            assert persona in available, (
                f"preset '{preset.id}' references unknown persona '{persona}' "
                f"(available: {sorted(available)})"
            )


def test_preset_colors_are_valid_hex():
    import re
    pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    for preset in load_presets():
        assert pattern.match(preset.color), (
            f"preset '{preset.id}' has invalid color '{preset.color}'"
        )


def test_get_preset_by_id():
    preset = get_preset("product_decision")
    assert preset is not None
    assert preset.id == "product_decision"
    assert "engineer" in preset.personas or "customer" in preset.personas


def test_get_preset_unknown_id():
    assert get_preset("does-not-exist") is None


def test_required_presets_present():
    """Make sure the core presets we promised are there."""
    required = ["product_decision", "career_choice", "strategic_bet"]
    available_ids = {p.id for p in load_presets()}
    for req in required:
        assert req in available_ids, f"missing required preset: {req}"


def test_wildcard_preset_uses_many_personas():
    """The Wild Card preset should use 5+ personas for max drama."""
    wildcard = get_preset("wildcard")
    if wildcard is not None:
        assert len(wildcard.personas) >= 5, (
            f"wildcard should use 5+ personas, uses {len(wildcard.personas)}"
        )
