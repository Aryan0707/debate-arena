"""Tests for the DebateResult rendering."""

from debate_arena.models import DebateResult, PersonaTurn


def test_to_markdown_basic():
    result = DebateResult(
        question="Test?",
        transcript=[
            PersonaTurn(persona="skeptic", round=1, phase="opening", content="No."),
            PersonaTurn(persona="optimist", round=1, phase="opening", content="Yes."),
        ],
        synthesis="Yes, with caveats.",
        config={"personas": ["skeptic", "optimist"]},
    )
    md = result.to_markdown()
    assert "# Debate: Test?" in md
    assert "## skeptic" in md
    assert "No." in md
    assert "## optimist" in md
    assert "Yes." in md
    assert "🏁 Final Synthesis" in md
    assert "Yes, with caveats." in md


def test_to_markdown_without_synthesis():
    result = DebateResult(
        question="Q",
        transcript=[PersonaTurn(persona="engineer", round=1, phase="opening", content="x")],
        synthesis=None,
        config={},
    )
    md = result.to_markdown()
    assert "🏁 Final Synthesis" not in md
    assert "## engineer" in md
