"""Lightweight share-link storage for debate arena.

A debate's transcript and synthesis can be stored here to get back a
short, shareable ID. The Gradio web UI exposes this as a "🔗 Share"
button after a debate completes.

Storage is a single SQLite file (~/.debate-arena/shares.db by default).
No schema migrations — if the schema ever changes, just delete the file.

Why SQLite: zero setup, atomic writes, survives crashes, no external
service. Good enough for a personal-scale share feature.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from debate_arena.models import DebateResult

DEFAULT_DB_PATH = Path.home() / ".debate-arena" / "shares.db"
SHARE_ID_LENGTH = 8  # → ~10^14 possible IDs, plenty


@dataclass
class ShareLink:
    """A stored share record."""

    id: str
    question: str
    transcript: list[dict]
    synthesis: str | None
    created_at: float
    config: dict
    total_usage: dict
    expires_at: float | None  # unix timestamp, or None for never


def _default_db_path() -> Path:
    """Resolve the share DB path, honoring the env var override."""
    override = os.environ.get("DEBATE_SHARE_DB")
    if override:
        return Path(override)
    return DEFAULT_DB_PATH


@contextmanager
def _connect(db_path: Path | None = None):
    """Context manager for a SQLite connection. Auto-creates the schema."""
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)
    try:
        # Pragmas for durability + small footprint
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create the shares table if it doesn't exist yet."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shares (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            transcript_json TEXT NOT NULL,
            synthesis TEXT,
            created_at REAL NOT NULL,
            config_json TEXT NOT NULL,
            total_usage_json TEXT NOT NULL,
            expires_at REAL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shares_created_at ON shares(created_at)")


def _generate_id(length: int = SHARE_ID_LENGTH) -> str:
    """URL-safe random ID, e.g. 'aB3xY9kP'."""
    return secrets.token_urlsafe(length)[:length]


def create_share(
    result: DebateResult,
    *,
    expires_in_days: int | None = None,
    db_path: Path | None = None,
) -> ShareLink:
    """Store a debate result and return a ShareLink with the new ID.

    Args:
        result: the completed debate to share
        expires_in_days: if set, the share auto-expires after this many days
        db_path: override the DB path (mostly for tests)

    Returns:
        A ShareLink with a short, unique ID.
    """
    import json

    share_id = _generate_id()
    now = time.time()
    expires_at = (now + expires_in_days * 86400) if expires_in_days else None

    with _connect(db_path) as conn:
        # If (extremely unlikely) collision, retry with a fresh ID
        for _ in range(5):
            try:
                conn.execute(
                    """
                    INSERT INTO shares (
                        id, question, transcript_json, synthesis,
                        created_at, config_json, total_usage_json, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        share_id,
                        result.question,
                        json.dumps([_turn_to_dict(t) for t in result.transcript]),
                        result.synthesis,
                        now,
                        json.dumps(result.config),
                        json.dumps(result.total_usage),
                        expires_at,
                    ),
                )
                break
            except sqlite3.IntegrityError:
                share_id = _generate_id()
        else:
            raise RuntimeError("could not generate a unique share id after 5 attempts")

    return ShareLink(
        id=share_id,
        question=result.question,
        transcript=[_turn_to_dict(t) for t in result.transcript],
        synthesis=result.synthesis,
        created_at=now,
        config=result.config,
        total_usage=result.total_usage,
        expires_at=expires_at,
    )


def get_share(share_id: str, *, db_path: Path | None = None) -> ShareLink | None:
    """Fetch a share by ID. Returns None if not found or expired."""
    import json

    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM shares WHERE id = ?", (share_id,)
        ).fetchone()

    if not row:
        return None

    # Check expiration
    expires_at = row[7]
    if expires_at is not None and time.time() > expires_at:
        return None

    return ShareLink(
        id=row[0],
        question=row[1],
        transcript=json.loads(row[2]),
        synthesis=row[3],
        created_at=row[4],
        config=json.loads(row[5]),
        total_usage=json.loads(row[6]),
        expires_at=expires_at,
    )


def list_shares(*, limit: int = 50, db_path: Path | None = None) -> list[ShareLink]:
    """List recent shares, newest first."""
    import json

    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM shares ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()

    return [
        ShareLink(
            id=r[0],
            question=r[1],
            transcript=json.loads(r[2]),
            synthesis=r[3],
            created_at=r[4],
            config=json.loads(r[5]),
            total_usage=json.loads(r[6]),
            expires_at=r[7],
        )
        for r in rows
    ]


def delete_share(share_id: str, *, db_path: Path | None = None) -> bool:
    """Delete a share by ID. Returns True if it existed."""
    with _connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM shares WHERE id = ?", (share_id,))
        return cursor.rowcount > 0


def cleanup_expired(*, db_path: Path | None = None) -> int:
    """Delete all expired shares. Returns the number deleted."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM shares WHERE expires_at IS NOT NULL AND expires_at < ?",
            (time.time(),),
        )
        return cursor.rowcount


def _turn_to_dict(turn) -> dict:
    """Convert a PersonaTurn to a JSON-safe dict."""
    return {
        "persona": turn.persona,
        "round": turn.round,
        "phase": turn.phase,
        "content": turn.content,
        "usage": turn.usage,
    }
