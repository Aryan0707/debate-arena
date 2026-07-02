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

from web_ui import build_ui, run_debate  # noqa: E402


def _consume(gen):
    return list(gen)


def test_generator_produces_status_and_transcript_yields():
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
    # Each yield is (status, synthesis, md)
    for status, synthesis, md in yields:
        assert isinstance(status, str)
        assert isinstance(synthesis, str)
        assert isinstance(md, str)

    # At least one status update per persona
    assert len(yields) >= 3
    # Final yield should be the completion message
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
    final_status, final_synthesis, final_md = yields[-1]
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
    # Should never shrink
    for i in range(1, len(md_lengths)):
        assert md_lengths[i] >= md_lengths[i - 1], (
            f"transcript shrank at yield {i}: {md_lengths[i-1]} -> {md_lengths[i]}"
        )
    # And should end significantly larger than it started
    assert md_lengths[-1] > md_lengths[0] + 500


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
    assert "question" in yields[0][0].lower() or "⚠️" in yields[0][0]


def test_generator_demo_mode_uses_stub_even_when_asking_for_anthropic():
    """When --demo is checked, the provider should be stub regardless of selection."""
    yields = _consume(
        run_debate(
            question="x",
            personas=["skeptic"],
            rounds=0,
            provider_name="anthropic",  # would normally need ANTHROPIC_API_KEY
            model="",
            use_demo=True,  # but demo mode forces stub
        )
    )
    # Should complete without raising
    final_status, _, _ = yields[-1]
    assert "complete" in final_status.lower()


def test_build_ui_constructs_gradio_blocks():
    """Smoke test: building the UI shouldn't raise."""
    import gradio as gr

    demo = build_ui()
    assert isinstance(demo, gr.Blocks)
