"""Tests for the debate orchestrator (run end-to-end with the stub provider)."""

from rich.console import Console

from debate_arena import DebateArena, DebateConfig
from debate_arena.providers import StubProvider


def _silent_console() -> Console:
    return Console(file=open("/dev/null", "w"))


def test_opening_round_only():
    arena = DebateArena(StubProvider(), console=_silent_console())
    result = arena.run(
        DebateConfig(
            question="Should we ship this?",
            personas=["skeptic", "optimist"],
            rounds=0,
            include_synthesis=False,
        )
    )
    assert len(result.transcript) == 2
    assert all(t.phase == "opening" for t in result.transcript)
    assert result.synthesis is None


def test_one_rebuttal_round_with_synthesis():
    arena = DebateArena(StubProvider(), console=_silent_console())
    result = arena.run(
        DebateConfig(
            question="Should we ship?",
            personas=["skeptic", "optimist", "engineer"],
            rounds=1,
        )
    )
    # 3 openings + 3 rebuttals = 6 turns
    assert len(result.transcript) == 6
    openings = [t for t in result.transcript if t.phase == "opening"]
    rebuttals = [t for t in result.transcript if t.phase == "rebuttal"]
    assert len(openings) == 3
    assert len(rebuttals) == 3
    assert result.synthesis
    assert "Should we ship?" in result.synthesis


def test_two_rounds_produces_more_turns():
    arena = DebateArena(StubProvider(), console=_silent_console())
    r1 = arena.run(
        DebateConfig(question="x", personas=["skeptic", "optimist", "engineer"], rounds=1)
    )
    r2 = arena.run(
        DebateConfig(question="x", personas=["skeptic", "optimist", "engineer"], rounds=2)
    )
    # r1: 3 openings + 3 rebuttals = 6 turns
    # r2: 3 openings + 6 rebuttals = 9 turns
    assert len(r1.transcript) == 6
    assert len(r2.transcript) == 9


def test_result_to_markdown_includes_synthesis():
    arena = DebateArena(StubProvider(), console=_silent_console())
    result = arena.run(
        DebateConfig(question="Pizza or sushi?", personas=["skeptic", "optimist"], rounds=1)
    )
    md = result.to_markdown()
    assert "# Debate: Pizza or sushi?" in md
    assert "skeptic" in md
    assert "optimist" in md
    assert "🏁 Final Synthesis" in md


def test_config_in_result():
    arena = DebateArena(StubProvider(), console=_silent_console())
    result = arena.run(
        DebateConfig(
            question="Q",
            personas=["engineer"],
            rounds=2,
            model="custom-model",
        )
    )
    assert result.config["personas"] == ["engineer"]
    assert result.config["rounds"] == 2
    assert result.config["model"] == "custom-model"


def test_synthesis_failure_does_not_crash():
    class BrokenProvider(StubProvider):
        def complete(self, *args, **kwargs):  # type: ignore[override]
            from debate_arena.providers.base import Completion, Message, ProviderError

            # Fail only when the moderator-style system prompt is present.
            for m in args[0] if args else []:
                if isinstance(m, Message) and "MODERATOR" in m.content.upper():
                    raise ProviderError("simulated failure")
            return Completion(content="ok", model="broken")

    arena = DebateArena(BrokenProvider(), console=_silent_console())
    result = arena.run(DebateConfig(question="Q", personas=["skeptic"], rounds=0))
    assert result.synthesis is None
    # But the opening turn should still be there.
    assert len(result.transcript) == 1
