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

# Default L2 cut-off for paraphrase-multilingual-MiniLM-L12-v2 distances.
# Empirical: dry-run #1 showed good matches at ~3.2–3.5 and clearly-off
# matches at ~4.8+. 4.0 splits the band; chunks above it get a
# low_confidence label so the caller can warn the user rather than
# presenting them as confident hits.
DEFAULT_CONFIDENCE_THRESHOLD = 4.0


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
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    where_source: str | None = None,
) -> list[dict]:
    """Return the top-``top_k`` chunks most similar to ``query``.

    Returns a list of dicts in ascending distance order (closer first):
      chunk_id, session_id, title, role, text, timestamp, source,
      distance, low_confidence.
    ``low_confidence`` is True when the L2 distance is strictly greater
    than ``confidence_threshold``; sqlite-vec always returns ``top_k``
    rows for a populated DB, so the flag is the only way for callers to
    distinguish "actually relevant" from "best of an irrelevant bunch".
    Empty DB or no matches -> empty list (no exception).

    ``where_source`` (when set) restricts results to that source. Because
    the sqlite-vec MATCH clause is evaluated before the JOIN-side
    filter, we over-sample the vector match (``top_k * 20``, floor 100)
    and then SQL-LIMIT down to ``top_k`` so the filter doesn't starve.
    """
    query_vec = embed_fn(query)

    if where_source is None:
        match_k = top_k
    else:
        match_k = max(top_k * 20, 100)

    sql = """
        SELECT c.chunk_id, c.session_id, c.title, c.role, c.text,
               c.timestamp, c.source, v.distance
        FROM chunk_vec v
        JOIN chunks c ON c.rowid = v.rowid
        WHERE v.embedding MATCH ?
          AND k = ?
    """
    params: list = [sqlite_vec.serialize_float32(query_vec), match_k]
    if where_source is not None:
        sql += " AND c.source = ?"
        params.append(where_source)
    sql += " ORDER BY v.distance LIMIT ?"
    params.append(top_k)

    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
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
            "low_confidence": float(r[7]) > confidence_threshold,
        }
        for r in rows
    ]
