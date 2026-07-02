"""Tests for DebateConfig."""

import pytest

from debate_arena.config import DebateConfig


def test_minimal_config():
    c = DebateConfig(question="Is this real?")
    assert c.question == "Is this real?"
    assert c.personas == ["skeptic", "optimist", "engineer"]
    assert c.rounds == 1
    assert c.include_synthesis is True


def test_empty_question_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        DebateConfig(question="")


def test_whitespace_question_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        DebateConfig(question="   \n\t  ")


def test_negative_rounds_rejected():
    with pytest.raises(ValueError, match="rounds must be"):
        DebateConfig(question="x", rounds=-1)


def test_empty_personas_rejected():
    with pytest.raises(ValueError, match="at least one persona"):
        DebateConfig(question="x", personas=[])


def test_personas_deduplicated_preserving_order():
    c = DebateConfig(
        question="x",
        personas=["engineer", "skeptic", "engineer", "optimist"],
    )
    assert c.personas == ["engineer", "skeptic", "optimist"]
