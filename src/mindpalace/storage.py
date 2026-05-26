"""SQLite + sqlite-vec storage for sessions, chunks, and vectors.

Raw chunk text is masked (via ``mindpalace.masking.mask_secrets``) at the
store boundary, so the persisted ``chunks.text`` never contains a plain
secret. raw immutable + derived data separation: ``chunks`` is the durable
raw layer (post-masking); ``chunk_vec`` is the derived vector index that
can be rebuilt from ``chunks`` if the embedding model changes.

Dedup is enforced by PRIMARY KEY conflicts (``INSERT OR IGNORE``):
session_id for the sessions table and ``{session_id}:{turn_id}`` for
chunks.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Callable

import sqlite_vec

from mindpalace.embedding import EMBEDDING_DIM
from mindpalace.masking import mask_secrets

EmbedFn = Callable[[str], list[float]]


_SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        title TEXT,
        extra_json TEXT,
        ingested_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES sessions(session_id),
        turn_id TEXT NOT NULL,
        source TEXT NOT NULL,
        title TEXT,
        role TEXT,
        text TEXT NOT NULL,
        timestamp TEXT,
        parent_id TEXT,
        ingested_at TEXT NOT NULL
    )
    """,
    f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vec USING vec0(
        embedding float[{EMBEDDING_DIM}]
    )
    """,
]


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with the sqlite-vec extension loaded."""
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_db(db_path: str) -> None:
    """Create the schema if it does not exist. Safe to call repeatedly."""
    conn = _connect(db_path)
    try:
        for stmt in _SCHEMA_SQL:
            conn.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def count_chunks(db_path: str) -> int:
    """Return the total number of chunk rows in the DB."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    finally:
        conn.close()


def store_session(
    db_path: str,
    session: dict,
    source: str,
    embed_fn: EmbedFn,
) -> dict:
    """Persist a parsed session: sessions row + chunks rows + chunk_vec rows.

    Each chunk's text is run through ``mask_secrets`` before insertion;
    the embedding is computed on the masked text and stored in the
    ``chunk_vec`` virtual table (rowid joined to ``chunks.rowid``).

    Idempotent: re-importing the same session is a no-op thanks to
    INSERT OR IGNORE on the primary keys.

    Returns counts: {sessions_inserted, chunks_inserted, dedup_skipped}.
    """
    now = datetime.now(timezone.utc).isoformat()
    session_id = session.get("session_id", "")
    title = session.get("title")
    extra_json = json.dumps(session.get("extra", {}), ensure_ascii=False)

    conn = _connect(db_path)
    try:
        sess_cur = conn.execute(
            "INSERT OR IGNORE INTO sessions "
            "(session_id, source, title, extra_json, ingested_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, source, title, extra_json, now),
        )
        sessions_inserted = sess_cur.rowcount

        chunks_inserted = 0
        dedup_skipped = 0
        for turn in session.get("turns", []):
            chunk_id = f"{session_id}:{turn.get('turn_id', '')}"
            masked_text = mask_secrets(turn.get("text", ""))

            ch_cur = conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(chunk_id, session_id, turn_id, source, title, role, text, "
                "timestamp, parent_id, ingested_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    chunk_id,
                    session_id,
                    turn.get("turn_id", ""),
                    source,
                    title,
                    turn.get("role", ""),
                    masked_text,
                    turn.get("timestamp", ""),
                    turn.get("parent_id"),
                    now,
                ),
            )
            if ch_cur.rowcount > 0:
                vector = embed_fn(masked_text)
                conn.execute(
                    "INSERT INTO chunk_vec(rowid, embedding) VALUES (?, ?)",
                    (ch_cur.lastrowid, sqlite_vec.serialize_float32(vector)),
                )
                chunks_inserted += 1
            else:
                dedup_skipped += 1

        conn.commit()
        return {
            "sessions_inserted": sessions_inserted,
            "chunks_inserted": chunks_inserted,
            "dedup_skipped": dedup_skipped,
        }
    finally:
        conn.close()
