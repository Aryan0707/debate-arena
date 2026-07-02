"""Tests for persona loading."""

import pytest

from debate_arena.personas import PERSONAS_DIR, Persona, load_persona, load_personas


def test_builtin_personas_exist():
    for pid in ["skeptic", "optimist", "engineer", "strategist", "moderator"]:
        p = load_persona(pid)
        assert isinstance(p, Persona)
        assert p.id == pid
        assert p.name
        assert p.system_prompt
        assert 0 <= p.temperature <= 2


def test_unknown_persona_raises():
    with pytest.raises(FileNotFoundError, match="not-a-persona"):
        load_persona("not-a-persona")


def test_load_multiple_preserves_order():
    ps = load_personas(["engineer", "optimist", "skeptic"])
    assert [p.id for p in ps] == ["engineer", "optimist", "skeptic"]


def test_opening_message_format():
    p = load_persona("skeptic")
    msg = p.render_user_message("Should I quit?")
    assert "QUESTION: Should I quit?" in msg
    assert "opening position" in msg


def test_rebuttal_message_includes_prior_turns():
    p = load_persona("skeptic")
    msg = p.render_user_message("Q?", prior_turns=["[optimist]\nWe should go for it"])
    assert "QUESTION: Q?" in msg
    assert "[optimist]" in msg
    assert "We should go for it" in msg
    assert "rebut" in msg.lower() or "respond" in msg.lower()


def test_personas_dir_is_correct():
    assert PERSONAS_DIR.exists()
    assert (PERSONAS_DIR / "skeptic.yaml").exists()
