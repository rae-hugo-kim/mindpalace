"""Semantic search over stored chunks.

The DB schema (sessions/chunks/chunk_vec) is owned by ``mindpalace.storage``.
``chunk_vec`` is the sqlite-vec virtual table whose rowid is kept in sync with
``chunks.rowid`` at insert time, so we can join the two tables to surface both
the vector distance and the original chunk metadata.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
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


def get_chunk_context(
    db_path: str,
    session_id: str,
    turn_id: str,
    window: int = 3,
) -> list[dict]:
    """Return the hit chunk plus up to ``window`` neighbors on each side.

    Neighbors are taken in chronological insert order within the same
    session (``ORDER BY rowid``), which mirrors the turn order produced
    by the parsers. The returned list is contiguous, clamps at session
    boundaries, and tags exactly one row with ``is_hit=True`` (the row
    whose ``turn_id`` matches the argument).

    Returns ``[]`` for unknown sessions or unknown turn ids — callers
    can treat absence as "no context available" without exception
    handling.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT chunk_id, session_id, turn_id, role, text, timestamp, source "
            "FROM chunks WHERE session_id = ? ORDER BY rowid",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()

    hit_idx = next((i for i, r in enumerate(rows) if r[2] == turn_id), -1)
    if hit_idx == -1:
        return []

    lo = max(0, hit_idx - window)
    hi = min(len(rows), hit_idx + window + 1)
    return [
        {
            "chunk_id": r[0],
            "session_id": r[1],
            "turn_id": r[2],
            "role": r[3],
            "text": r[4],
            "timestamp": r[5],
            "source": r[6],
            "is_hit": (lo + offset) == hit_idx,
        }
        for offset, r in enumerate(rows[lo:hi])
    ]


def _parse_iso(ts: str) -> datetime | None:
    """Tolerant ISO-8601 parse. Returns None on empty/unparseable input.

    The corpus mixes Z-suffixed and offset-bearing timestamps; the
    fromisoformat fallback accepts trailing Z as +00:00 on Python 3.11+.
    """
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def find_neighbors(
    db_path: str,
    session_id: str,
    window_days: float = 3.0,
) -> list[dict]:
    """Return opposite-source sessions whose timestamps fall within
    ±``window_days`` of this session's anchor.

    AC6 — the "약한 학습-작업 연결". A chat session (학습) and a code
    session (작업) on adjacent days are likely about the same problem,
    so this function joins them by time proximity, not content.

    Anchor = MIN(chunks.timestamp) for the given session. Candidates
    are sessions whose source differs and whose own anchor falls in
    the window. Result rows include ``time_delta_days`` (signed:
    positive = candidate is later than the query session).
    Returns ``[]`` when the session_id is unknown or carries no
    parseable timestamps.
    """
    conn = sqlite3.connect(db_path)
    try:
        anchor_row = conn.execute(
            "SELECT s.source, MIN(c.timestamp) "
            "FROM sessions s LEFT JOIN chunks c ON c.session_id = s.session_id "
            "WHERE s.session_id = ?",
            (session_id,),
        ).fetchone()

        if anchor_row is None or anchor_row[0] is None:
            return []
        my_source, my_anchor_ts = anchor_row
        my_anchor = _parse_iso(my_anchor_ts or "")
        if my_anchor is None:
            return []

        candidates = conn.execute(
            "SELECT s.session_id, s.source, s.title, MIN(c.timestamp) AS anchor "
            "FROM sessions s JOIN chunks c ON c.session_id = s.session_id "
            "WHERE s.source != ? AND s.session_id != ? "
            "GROUP BY s.session_id "
            "ORDER BY anchor",
            (my_source, session_id),
        ).fetchall()
    finally:
        conn.close()

    window = timedelta(days=window_days)
    out: list[dict] = []
    for sid, source, title, anchor_ts in candidates:
        cand_anchor = _parse_iso(anchor_ts or "")
        if cand_anchor is None:
            continue
        delta = cand_anchor - my_anchor
        if abs(delta) <= window:
            out.append(
                {
                    "session_id": sid,
                    "source": source,
                    "title": title,
                    "anchor_timestamp": anchor_ts,
                    "time_delta_days": delta.total_seconds() / 86400.0,
                }
            )
    return out
