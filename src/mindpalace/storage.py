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
from mindpalace.obs import get_logger

EmbedFn = Callable[[str], list[float]]

_log = get_logger("mindpalace.storage")


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
    """
    CREATE TABLE IF NOT EXISTS code_meta (
        session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),
        files_json TEXT NOT NULL,
        commands_json TEXT NOT NULL,
        tools_json TEXT NOT NULL,
        error_count INTEGER NOT NULL DEFAULT 0
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
    conn.execute("PRAGMA foreign_keys = ON")
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


def reindex_vectors(db_path: str, embed_fn: EmbedFn) -> dict:
    """Rebuild the derived ``chunk_vec`` index from the raw ``chunks`` rows.

    The seed treats ``chunks`` (post-masking) as the immutable raw layer
    and ``chunk_vec`` as derived data that must be regeneratable when the
    embedding model or vector schema changes. This drops every vector and
    re-embeds each chunk's stored text, reinserting with the same rowid so
    the chunks↔chunk_vec join stays aligned.

    Returns {"reindexed": <count>}.
    """
    conn = _connect(db_path)
    try:
        # Drop and recreate so a dimension change (model upgrade) is
        # transparently handled — DELETE alone keeps the old schema.
        conn.execute("DROP TABLE IF EXISTS chunk_vec")
        conn.execute(
            f"CREATE VIRTUAL TABLE chunk_vec USING vec0(embedding float[{EMBEDDING_DIM}])"
        )
        rows = conn.execute("SELECT rowid, text FROM chunks ORDER BY rowid").fetchall()
        reindexed = 0
        for rowid, text in rows:
            vector = embed_fn(text)
            conn.execute(
                "INSERT INTO chunk_vec(rowid, embedding) VALUES (?, ?)",
                (rowid, sqlite_vec.serialize_float32(vector)),
            )
            reindexed += 1
        conn.commit()
    finally:
        conn.close()

    _log.info("reindex complete reindexed=%d", reindexed)
    return {"reindexed": reindexed}


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

    Returns counts: {sessions_inserted, chunks_inserted, dedup_skipped,
    masked, embed_failures}. ``masked`` is the number of chunks whose
    text was altered by secret masking; ``embed_failures`` is the number
    of chunks dropped because ``embed_fn`` raised (AC15 operational
    signals, also written to the ``mindpalace.storage`` log).
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

        code_meta = session.get("code_meta")
        if code_meta:
            # Commands are free text and may contain secrets (e.g.
            # `export TOKEN=sk-...`), so mask them like chunk text. Files
            # and tool names are structural and stored verbatim. Keyed on
            # session_id PRIMARY KEY → idempotent on reimport (derived
            # index, rebuildable from raw).
            masked_commands = [mask_secrets(c) for c in code_meta.get("commands", [])]
            conn.execute(
                "INSERT OR IGNORE INTO code_meta "
                "(session_id, files_json, commands_json, tools_json, error_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    json.dumps(code_meta.get("files", []), ensure_ascii=False),
                    json.dumps(masked_commands, ensure_ascii=False),
                    json.dumps(code_meta.get("tools", []), ensure_ascii=False),
                    int(code_meta.get("error_count", 0)),
                ),
            )

        chunks_inserted = 0
        dedup_skipped = 0
        masked = 0
        embed_failures = 0
        for turn in session.get("turns", []):
            raw_text = turn.get("text", "")
            if not raw_text.strip():
                continue
            chunk_id = f"{session_id}:{turn.get('turn_id', '')}"
            masked_text = mask_secrets(raw_text)
            if masked_text != raw_text:
                masked += 1

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
                try:
                    vector = embed_fn(masked_text)
                except Exception:
                    # Drop the just-claimed chunk row so chunks/chunk_vec
                    # stay in sync; the absent chunk_id lets a later
                    # reimport retry the embedding.
                    conn.execute("DELETE FROM chunks WHERE rowid = ?", (ch_cur.lastrowid,))
                    embed_failures += 1
                    _log.warning(
                        "embedding failed for chunk %s — skipped (will retry on reimport)",
                        chunk_id,
                    )
                    continue
                conn.execute(
                    "INSERT INTO chunk_vec(rowid, embedding) VALUES (?, ?)",
                    (ch_cur.lastrowid, sqlite_vec.serialize_float32(vector)),
                )
                chunks_inserted += 1
            else:
                dedup_skipped += 1

        conn.commit()
        _log.info(
            "import session=%s source=%s sessions_inserted=%d chunks_inserted=%d "
            "dedup_skipped=%d masked=%d embed_failures=%d",
            session_id, source, sessions_inserted, chunks_inserted,
            dedup_skipped, masked, embed_failures,
        )
        return {
            "sessions_inserted": sessions_inserted,
            "chunks_inserted": chunks_inserted,
            "dedup_skipped": dedup_skipped,
            "masked": masked,
            "embed_failures": embed_failures,
        }
    finally:
        conn.close()
