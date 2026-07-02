"""Tests for the shares storage layer."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from debate_arena.models import DebateResult, PersonaTurn
from debate_arena.shares import (
    cleanup_expired,
    create_share,
    delete_share,
    get_share,
    list_shares,
)


@pytest.fixture
def tmp_db(monkeypatch):
    """Create a temp DB path and point the shares module at it."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)  # let the module create it
    monkeypatch.setenv("DEBATE_SHARE_DB", path)
    yield Path(path)
    if os.path.exists(path):
        os.unlink(path)


def _make_result(question: str = "Test Q?") -> DebateResult:
    return DebateResult(
        question=question,
        transcript=[
            PersonaTurn(persona="skeptic", round=1, phase="opening", content="Skeptic content"),
            PersonaTurn(persona="optimist", round=1, phase="opening", content="Optimist content"),
        ],
        synthesis="Final synthesis text.",
        config={"personas": ["skeptic", "optimist"], "rounds": 1},
        total_usage={"input_tokens": 100},
    )


def test_create_share_returns_link_with_id(tmp_db):
    result = _make_result()
    link = create_share(result, db_path=tmp_db)
    assert link.id
    assert len(link.id) >= 6  # at least 6 chars
    assert link.question == "Test Q?"
    assert link.synthesis == "Final synthesis text."
    assert len(link.transcript) == 2


def test_get_share_roundtrip(tmp_db):
    result = _make_result(question="Roundtrip Q?")
    created = create_share(result, db_path=tmp_db)
    fetched = get_share(created.id, db_path=tmp_db)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.question == "Roundtrip Q?"
    assert fetched.synthesis == "Final synthesis text."
    assert fetched.transcript[0]["persona"] == "skeptic"
    assert fetched.transcript[0]["content"] == "Skeptic content"


def test_get_share_returns_none_for_missing(tmp_db):
    assert get_share("nonexistent", db_path=tmp_db) is None


def test_get_share_respects_expiration(tmp_db):
    result = _make_result()
    # Create a share that expired 1 hour ago
    link = create_share(result, db_path=tmp_db)
    # Manually set its expiration to the past via direct DB access
    from debate_arena.shares import _connect
    with _connect(tmp_db) as conn:
        conn.execute(
            "UPDATE shares SET expires_at = ? WHERE id = ?",
            (time.time() - 3600, link.id),
        )
    assert get_share(link.id, db_path=tmp_db) is None


def test_create_share_with_expiration(tmp_db):
    result = _make_result()
    link = create_share(result, expires_in_days=7, db_path=tmp_db)
    assert link.expires_at is not None
    # Should still be fetchable
    assert get_share(link.id, db_path=tmp_db) is not None


def test_list_shares_newest_first(tmp_db):
    r1 = _make_result(question="First")
    r2 = _make_result(question="Second")
    create_share(r1, db_path=tmp_db)
    time.sleep(0.01)
    create_share(r2, db_path=tmp_db)
    links = list_shares(db_path=tmp_db)
    assert len(links) == 2
    # Newest first
    assert links[0].question == "Second"
    assert links[1].question == "First"


def test_delete_share(tmp_db):
    result = _make_result()
    link = create_share(result, db_path=tmp_db)
    assert delete_share(link.id, db_path=tmp_db) is True
    assert get_share(link.id, db_path=tmp_db) is None
    # Deleting again returns False
    assert delete_share(link.id, db_path=tmp_db) is False


def test_cleanup_expired(tmp_db):
    from debate_arena.shares import _connect
    r = _make_result()
    # Create an expired one
    expired = create_share(r, db_path=tmp_db)
    with _connect(tmp_db) as conn:
        conn.execute(
            "UPDATE shares SET expires_at = ? WHERE id = ?",
            (time.time() - 1, expired.id),
        )
    # And a fresh one
    fresh = create_share(r, db_path=tmp_db)

    deleted = cleanup_expired(db_path=tmp_db)
    assert deleted == 1
    assert get_share(expired.id, db_path=tmp_db) is None
    assert get_share(fresh.id, db_path=tmp_db) is not None


def test_create_share_unique_ids(tmp_db):
    """Generated IDs should be unique across many creates."""
    result = _make_result()
    ids = {create_share(result, db_path=tmp_db).id for _ in range(20)}
    assert len(ids) == 20


def test_share_persists_complex_transcript(tmp_db):
    """Multi-round debate should round-trip fully."""
    result = DebateResult(
        question="Complex?",
        transcript=[
            PersonaTurn(persona="skeptic", round=1, phase="opening", content="S1"),
            PersonaTurn(persona="optimist", round=1, phase="opening", content="O1"),
            PersonaTurn(persona="engineer", round=1, phase="opening", content="E1"),
            PersonaTurn(persona="skeptic", round=1, phase="rebuttal", content="S1r"),
            PersonaTurn(persona="optimist", round=1, phase="rebuttal", content="O1r"),
            PersonaTurn(persona="engineer", round=1, phase="rebuttal", content="E1r"),
        ],
        synthesis="Final.",
        config={"personas": ["skeptic", "optimist", "engineer"], "rounds": 1},
        total_usage={},
    )
    link = create_share(result, db_path=tmp_db)
    fetched = get_share(link.id, db_path=tmp_db)
    assert fetched is not None
    assert len(fetched.transcript) == 6
    assert fetched.transcript[0]["phase"] == "opening"
    assert fetched.transcript[3]["phase"] == "rebuttal"
    assert fetched.transcript[3]["persona"] == "skeptic"
