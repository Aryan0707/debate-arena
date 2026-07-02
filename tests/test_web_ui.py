"""Tests for the Gradio web UI generator.

These tests don't launch the full Gradio server (that's slow and
network-dependent). They exercise the streaming generator that the
Gradio button handler calls, ensuring it yields the right shape and
the right number of times.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the web_ui module importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from web_ui import build_ui, render_persona_chips, run_debate  # noqa: E402


def _consume(gen):
    return list(gen)


def test_generator_yields_4_tuples():
    """Each yield should be (status, synthesis, md, chips_html)."""
    yields = _consume(
        run_debate(
            question="Is this thing on?",
            personas=["skeptic", "optimist"],
            rounds=0,
            provider_name="stub",
            model="",
            use_demo=True,
        )
    )
    for yield_val in yields:
        assert len(yield_val) == 4, f"expected 4-tuple, got {len(yield_val)}"
        status, synthesis, md, chips = yield_val
        assert isinstance(status, str)
        assert isinstance(synthesis, str)
        assert isinstance(md, str)
        assert isinstance(chips, str)
    assert len(yields) >= 3
    assert "complete" in yields[-1][0].lower() or "✅" in yields[-1][0]


def test_generator_final_synthesis_is_populated():
    yields = _consume(
        run_debate(
            question="x",
            personas=["engineer"],
            rounds=0,
            provider_name="stub",
            model="",
            use_demo=True,
        )
    )
    final_status, final_synthesis, final_md, _ = yields[-1]
    assert final_synthesis
    assert "Bottom line" in final_synthesis or "Synthesis" in final_synthesis


def test_generator_transcript_grows_monotonically():
    """The transcript markdown should grow as the debate progresses."""
    yields = _consume(
        run_debate(
            question="x",
            personas=["skeptic", "optimist", "engineer"],
            rounds=1,
            provider_name="stub",
            model="",
            use_demo=True,
        )
    )
    md_lengths = [len(y[2]) for y in yields]
    for i in range(1, len(md_lengths)):
        assert md_lengths[i] >= md_lengths[i - 1], (
            f"transcript shrank at yield {i}: {md_lengths[i - 1]} -> {md_lengths[i]}"
        )
    assert md_lengths[-1] > md_lengths[0] + 500


def test_generator_chips_html_present():
    """The chips HTML should reflect the selected personas."""
    yields = _consume(
        run_debate(
            question="x",
            personas=["skeptic", "engineer"],
            rounds=0,
            provider_name="stub",
            model="",
            use_demo=True,
        )
    )
    final_chips = yields[-1][3]
    assert "Skeptic" in final_chips
    assert "Engineer" in final_chips


def test_generator_handles_empty_question():
    yields = _consume(
        run_debate(
            question="",
            personas=["skeptic"],
            rounds=0,
            provider_name="stub",
            model="",
            use_demo=True,
        )
    )
    assert len(yields) >= 1
    # The status should be an error banner
    assert "status-banner error" in yields[0][0] or "⚠️" in yields[0][0]


def test_generator_handles_no_personas():
    yields = _consume(
        run_debate(
            question="valid question",
            personas=[],
            rounds=0,
            provider_name="stub",
            model="",
            use_demo=True,
        )
    )
    assert len(yields) >= 1
    assert "status-banner error" in yields[0][0] or "⚠️" in yields[0][0]


def test_generator_demo_mode_uses_stub():
    yields = _consume(
        run_debate(
            question="x",
            personas=["skeptic"],
            rounds=0,
            provider_name="anthropic",
            model="",
            use_demo=True,
        )
    )
    final_status, _, _, _ = yields[-1]
    assert "complete" in final_status.lower()


def test_build_ui_constructs_gradio_blocks():
    import gradio as gr

    demo = build_ui()
    assert isinstance(demo, gr.Blocks)


def test_render_persona_chips_empty():
    html = render_persona_chips([])
    assert "empty-chips" in html
    assert "No personas selected" in html


def test_render_persona_chips_populated():
    html = render_persona_chips(["skeptic", "engineer"])
    assert "Skeptic" in html
    assert "Engineer" in html
    # Should include the CSS custom property for color
    assert "--chip-color" in html


def test_render_persona_chips_handles_unknown_persona():
    """Shouldn't crash on an unknown persona id."""
    html = render_persona_chips(["skeptic", "made-up-persona"])
    assert "Skeptic" in html
    assert "made-up-persona" in html.lower().replace(" ", "-") or "Made Up Persona" in html
