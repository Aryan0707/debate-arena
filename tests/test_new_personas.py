"""Tests for the new personas added in v0.2: hacker, regulator, philosopher,
trader, customer, first-principles."""

from __future__ import annotations

import pytest

from debate_arena.providers import StubProvider
from debate_arena.providers.base import Message
from debate_arena.personas import load_persona


NEW_PERSONA_IDS = [
    "hacker",
    "regulator",
    "philosopher",
    "trader",
    "customer",
    "first-principles",
]


@pytest.mark.parametrize("pid", NEW_PERSONA_IDS)
def test_new_persona_loads(pid):
    p = load_persona(pid)
    assert p.id == pid
    assert p.name
    assert p.system_prompt
    assert 0 <= p.temperature <= 2


@pytest.mark.parametrize("pid", NEW_PERSONA_IDS)
def test_new_persona_opening_message_works(pid):
    p = load_persona(pid)
    msg = p.render_user_message("Big question?")
    assert "Big question?" in msg
    assert "opening" in msg.lower() or "persona" in msg.lower() or "position" in msg.lower()


@pytest.mark.parametrize("pid", NEW_PERSONA_IDS)
def test_stub_provider_can_generate_for_new_persona(pid):
    """Every new persona should have a stub template, so demo mode works for them."""
    p = StubProvider()
    completion = p.complete(
        [
            Message(
                role="system",
                # Match the "You are the X" / "You are X" pattern the stub detects
                content=(
                    f"You are the {pid.replace('-', ' ').upper()} in a multi-agent debate. "
                    "Your job is to engage with the question in your unique voice."
                ),
            ),
            Message(role="user", content="QUESTION: Test question here"),
        ]
    )
    assert completion.content
    # Every new persona's template includes the question literally
    assert "Test question here" in completion.content


def test_total_persona_count_is_eleven():
    """Sanity: we should now have 11 personas (5 original + 6 new)."""
    from debate_arena.personas import PERSONAS_DIR
    yaml_files = list(PERSONAS_DIR.glob("*.yaml"))
    assert len(yaml_files) == 11, f"expected 11 personas, found {len(yaml_files)}: {[p.stem for p in yaml_files]}"
