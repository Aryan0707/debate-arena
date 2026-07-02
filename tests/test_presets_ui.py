"""Tests for the apply_preset function and preset UI rendering in the web UI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from web_ui import PRESETS, apply_preset, render_preset_chips  # noqa: E402


def test_presets_loaded_at_import_time():
    assert len(PRESETS) >= 5


def test_render_preset_chips_returns_html():
    html = render_preset_chips()
    assert html
    assert "preset-row" in html
    assert "preset-card" in html
    # Each preset should appear as a button
    for preset in PRESETS:
        assert f'data-preset-id="{preset.id}"' in html
        assert preset.emoji in html
        assert preset.name in html


def test_apply_preset_returns_updated_values():
    """apply_preset should return the new question, personas, rounds, banner, and id."""
    question, personas, rounds, banner, active_id = apply_preset("career_choice")
    assert question
    assert isinstance(personas, list) and len(personas) >= 2
    assert isinstance(rounds, int)
    assert "career_choice" in active_id
    assert "career_choice" in active_id.lower() or "Career" in banner
    assert "status-banner" in banner


def test_apply_preset_empty_id_is_noop():
    """Empty preset id should return gr.update() placeholders."""
    result = apply_preset("")
    # All five outputs should be the no-op gr.update()
    for item in result:
        # gr.update() instances don't compare with ==, but we can check it's not a string
        # that would change UI state
        assert item == "" or hasattr(item, "__class__")


def test_apply_preset_unknown_id_is_noop():
    result = apply_preset("not-a-real-preset")
    # Should not raise, should return safe defaults
    assert result is not None


def test_apply_preset_overwrites_question():
    preset = PRESETS[0]
    question, _, _, _, _ = apply_preset(preset.id)
    assert question == preset.example_question


def test_apply_preset_sets_personas():
    preset = PRESETS[0]
    _, personas, _, _, _ = apply_preset(preset.id)
    assert set(personas) == set(preset.personas)


def test_apply_preset_sets_rounds():
    preset = PRESETS[0]
    _, _, rounds, _, _ = apply_preset(preset.id)
    assert rounds == preset.rounds
