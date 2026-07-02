"""Tests for the stub provider (used in demo mode and as a no-API fallback)."""

from debate_arena.providers import StubProvider
from debate_arena.providers.base import Message


def test_stub_returns_content():
    p = StubProvider()
    completion = p.complete(
        [
            Message(role="system", content="You are the SKEPTIC in a debate."),
            Message(role="user", content="QUESTION: Is pizza good?"),
        ]
    )
    assert completion.content
    assert completion.model == "stub-v1"
    # usage may be empty or contain stub markers; both are acceptable
    assert isinstance(completion.usage, dict)


def test_stub_detects_persona_from_system_prompt():
    p = StubProvider()
    for persona in ["skeptic", "optimist", "engineer", "strategist", "moderator"]:
        completion = p.complete(
            [
                Message(role="system", content=f"You are the {persona.upper()} in a debate."),
                Message(role="user", content="QUESTION: Test question"),
            ]
        )
        assert completion.content
        # Each persona template references the question literally.
        assert "Test question" in completion.content


def test_stub_handles_rebuttal_phase():
    p = StubProvider()
    completion = p.complete(
        [
            Message(role="system", content="You are the ENGINEER in a debate."),
            Message(
                role="user",
                content=(
                    "QUESTION: Test\n\n"
                    "OTHER PERSONAS HAVE SAID (round 1):\n\n"
                    "[optimist]\nWe should ship it"
                ),
            ),
        ]
    )
    assert "Rebuttal:" in completion.content or "rebut" in completion.content.lower()


def test_stub_handles_empty_prior_turns():
    p = StubProvider()
    completion = p.complete(
        [
            Message(role="system", content="You are the OPTIMIST."),
            Message(role="user", content="QUESTION: go time?"),
        ]
    )
    # The opening template should produce a sentence with the question.
    assert "go time?" in completion.content
