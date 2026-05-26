"""Semantic search over stored chunks.

The DB schema (sessions/chunks/chunk_vec) is owned by ``mindpalace.storage``.
``chunk_vec`` is the sqlite-vec virtual table whose rowid is kept in sync with
``chunks.rowid`` at insert time, so we can join the two tables to surface both
the vector distance and the original chunk metadata.
"""
from __future__ import annotations

import sqlite3
from typing import Callable

import sqlite_vec

EmbedFn = Callable[[str], list[float]]


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def search(
    db_path: str,
    query: str,
    embed_fn: EmbedFn,
    top_k: int = 5,
) -> list[dict]:
    """Return the top-``top_k`` chunks most similar to ``query``.

    Returns a list of dicts in ascending distance order (closer first):
      chunk_id, session_id, title, role, text, timestamp, source, distance.
    Empty DB or no matches -> empty list (no exception).
    """
    query_vec = embed_fn(query)

    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT c.chunk_id, c.session_id, c.title, c.role, c.text,
                   c.timestamp, c.source, v.distance
            FROM chunk_vec v
            JOIN chunks c ON c.rowid = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
            ORDER BY v.distance
            """,
            (sqlite_vec.serialize_float32(query_vec), top_k),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "chunk_id": r[0],
            "session_id": r[1],
            "title": r[2],
            "role": r[3],
            "text": r[4],
            "timestamp": r[5],
            "source": r[6],
            "distance": float(r[7]),
        }
        for r in rows
    ]
