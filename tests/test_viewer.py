"""Tests for the FastAPI public share viewer."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from debate_arena.models import DebateResult, PersonaTurn
from debate_arena.shares import create_share
from debate_arena.viewer import app


@pytest.fixture
def client_with_share(monkeypatch):
    """Create a TestClient with a share pre-loaded in a temp DB."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    monkeypatch.setenv("DEBATE_SHARE_DB", path)

    result = DebateResult(
        question="Should I switch careers?",
        transcript=[
            PersonaTurn(
                persona="skeptic", round=1, phase="opening",
                content="The risks are real. Consider this carefully.",
            ),
            PersonaTurn(
                persona="optimist", round=1, phase="opening",
                content="Life is short. Go for it!",
            ),
        ],
        synthesis="It depends on your runway and risk tolerance.",
        config={"personas": ["skeptic", "optimist"], "rounds": 1},
        total_usage={},
    )
    link = create_share(result, db_path=Path(path))
    yield TestClient(app), link.id
    if os.path.exists(path):
        os.unlink(path)


def test_root_endpoint(client_with_share):
    client, _ = client_with_share
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"].startswith("Debate Arena")
    assert "endpoints" in data


def test_health_endpoint(client_with_share):
    client, _ = client_with_share
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_share_view_html_returns_200(client_with_share):
    client, share_id = client_with_share
    r = client.get(f"/share/{share_id}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    # The question is in the hero
    assert "Should I switch careers?" in body
    # The synthesis is in the synthesis section
    assert "It depends on your runway" in body
    # Both personas appear as cards
    assert "Skeptic" in body
    assert "Optimist" in body
    # The CSS is embedded
    assert "persona-emoji" in body


def test_share_view_html_404_for_missing(client_with_share):
    client, _ = client_with_share
    r = client.get("/share/does-not-exist")
    assert r.status_code == 404


def test_share_view_json_returns_full_data(client_with_share):
    client, share_id = client_with_share
    r = client.get(f"/share/{share_id}/json")
    assert r.status_code == 200
    data = r.json()
    assert data["question"] == "Should I switch careers?"
    assert data["synthesis"] == "It depends on your runway and risk tolerance."
    assert len(data["transcript"]) == 2
    assert data["transcript"][0]["persona"] == "skeptic"
    assert "config" in data


def test_share_view_json_404_for_missing(client_with_share):
    client, _ = client_with_share
    r = client.get("/share/does-not-exist/json")
    assert r.status_code == 404


def test_share_view_html_escapes_question(client_with_share):
    """Make sure HTML in the question is properly escaped."""
    client, _ = client_with_share
    # Try to create a share with HTML in it
    from debate_arena.shares import _connect
    with _connect() as conn:
        conn.execute(
            "INSERT INTO shares (id, question, transcript_json, synthesis, created_at, config_json, total_usage_json, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "xss-test",
                "<script>alert('xss')</script>",
                "[]",
                "ok",
                1000000000.0,
                "{}",
                "{}",
                None,
            ),
        )
    r = client.get("/share/xss-test")
    assert r.status_code == 200
    # The script tag should be escaped, not executed
    assert "<script>alert" not in r.text
    assert "&lt;script&gt;" in r.text or "&#x27;" in r.text or "alert" not in r.text.split("</style>")[1].split("<footer")[0]
