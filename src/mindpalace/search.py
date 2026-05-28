"""Semantic search over stored chunks.

The DB schema (sessions/chunks/chunk_vec) is owned by ``mindpalace.storage``.
``chunk_vec`` is the sqlite-vec virtual table whose rowid is kept in sync with
``chunks.rowid`` at insert time, so we can join the two tables to surface both
the vector distance and the original chunk metadata.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta
from typing import Callable

import sqlite_vec

from mindpalace.embedding import embed_query
from mindpalace.obs import get_logger

EmbedFn = Callable[[str], list[float]]

_log = get_logger("mindpalace.search")

# Default L2 cut-off for multilingual-e5-large normalized vectors.
# Empirically (small MCP corpus): on-topic ~0.53, off-topic ~0.71-0.75.
# 0.7 splits the band; chunks above get a low_confidence label so the
# caller can warn rather than presenting them as confident hits. Tune
# per corpus via the ``--min-confidence`` flag.
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def _chunk_filter_sql(
    where_source: str | None,
    where_since: str | None,
    where_until: str | None,
    where_title_like: str | None,
    where_file_like: str | None,
) -> tuple[str, list]:
    """Build the AND-clauses shared by semantic and keyword search.

    Returns (sql_fragment, params). Column refs use the alias ``c`` for
    the chunks table.
    """
    sql = ""
    params: list = []
    if where_source is not None:
        sql += " AND c.source = ?"
        params.append(where_source)
    if where_since is not None:
        sql += " AND c.timestamp >= ?"
        params.append(where_since)
    if where_until is not None:
        sql += " AND c.timestamp <= ?"
        params.append(where_until)
    if where_title_like is not None:
        sql += " AND c.title LIKE ?"
        params.append(f"%{where_title_like}%")
    if where_file_like is not None:
        sql += (
            " AND c.session_id IN "
            "(SELECT session_id FROM code_meta WHERE files_json LIKE ?)"
        )
        params.append(f"%{where_file_like}%")
    return sql, params


def search(
    db_path: str,
    query: str,
    embed_fn: EmbedFn,
    top_k: int = 5,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    where_source: str | None = None,
    where_since: str | None = None,
    where_until: str | None = None,
    where_title_like: str | None = None,
    where_file_like: str | None = None,
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

    Meta filters (all optional, AND-combined):
      ``where_source``      exact source match (e.g. "code" / "chat")
      ``where_since``       inclusive lower bound on chunk timestamp
                            (lexicographic ISO-8601 compare)
      ``where_until``       inclusive upper bound on chunk timestamp
      ``where_title_like``  case-insensitive substring match on title
      ``where_file_like``   substring match on a code session's extracted
                            file paths (``code_meta.files_json``); only
                            code sessions carry these, so this implicitly
                            restricts to source="code"

    Because the sqlite-vec MATCH clause is evaluated before the
    JOIN-side filters, whenever any filter is active we over-sample the
    vector match (``top_k * 20``, floor 100) and SQL-LIMIT back to
    ``top_k`` so the filters don't starve the result set.
    """
    t0 = time.perf_counter()
    # e5 is asymmetric: queries need the "query:" prefix that embed_fn
    # (used for stored passages) does not apply. Use embed_query here.
    query_vec = embed_query(query)

    has_filter = any(
        f is not None
        for f in (
            where_source,
            where_since,
            where_until,
            where_title_like,
            where_file_like,
        )
    )
    match_k = max(top_k * 20, 100) if has_filter else top_k

    sql = """
        SELECT c.chunk_id, c.session_id, c.title, c.role, c.text,
               c.timestamp, c.source, v.distance
        FROM chunk_vec v
        JOIN chunks c ON c.rowid = v.rowid
        WHERE v.embedding MATCH ?
          AND k = ?
    """
    params: list = [sqlite_vec.serialize_float32(query_vec), match_k]
    filter_sql, filter_params = _chunk_filter_sql(
        where_source, where_since, where_until, where_title_like, where_file_like
    )
    sql += filter_sql
    params += filter_params
    sql += " ORDER BY v.distance LIMIT ?"
    params.append(top_k)

    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    results = [
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
            "match": "semantic",
        }
        for r in rows
    ]
    latency_ms = (time.perf_counter() - t0) * 1000.0
    _log.info("search query=%r latency_ms=%.2f hits=%d", query, latency_ms, len(results))
    return results


def keyword_search(
    db_path: str,
    query: str,
    top_k: int = 5,
    where_source: str | None = None,
    where_since: str | None = None,
    where_until: str | None = None,
    where_title_like: str | None = None,
    where_file_like: str | None = None,
) -> list[dict]:
    """Substring (LIKE) search over chunk text — the lexical complement to
    semantic ``search``.

    Dense embeddings represent rare proper nouns poorly (e.g. a drug brand
    name transliterated into Korean), so the semantic ranker buries exact
    matches under unrelated noise. A literal substring match recovers them.
    Results share the semantic shape but carry ``match="keyword"`` and a
    ``distance``/``low_confidence`` of None/False; ordered most-recent first.
    The same meta filters apply.

    Query is trimmed; an empty/whitespace-only query short-circuits to ``[]``
    so we never run a wildcard ``%%`` scan. Matching uses ``str.casefold`` via
    a registered SQLite function so non-ASCII case (e.g. ``Café``/``CAFÉ``)
    folds too — SQLite's default ``LIKE`` only folds ASCII A–Z.
    """
    q = (query or "").strip()
    if not q:
        return []
    sql = (
        "SELECT c.chunk_id, c.session_id, c.title, c.role, c.text, "
        "c.timestamp, c.source FROM chunks c WHERE mp_casefold(c.text) LIKE ?"
    )
    params: list = [f"%{q.casefold()}%"]
    filter_sql, filter_params = _chunk_filter_sql(
        where_source, where_since, where_until, where_title_like, where_file_like
    )
    sql += filter_sql
    sql += " ORDER BY c.timestamp DESC LIMIT ?"
    params += filter_params
    params.append(top_k)

    conn = sqlite3.connect(db_path)
    conn.create_function("mp_casefold", 1, lambda s: s.casefold() if s else s, deterministic=True)
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
            "distance": None,
            "low_confidence": False,
            "match": "keyword",
        }
        for r in rows
    ]


def hybrid_search(
    db_path: str,
    query: str,
    embed_fn: EmbedFn,
    top_k: int = 5,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    where_source: str | None = None,
    where_since: str | None = None,
    where_until: str | None = None,
    where_title_like: str | None = None,
    where_file_like: str | None = None,
) -> dict:
    """Run keyword + semantic search and return both, de-duplicated.

    Returns {"keyword": [...], "semantic": [...]} where the semantic list
    excludes any chunk already present as a keyword (exact) match — keyword
    hits are the higher-confidence answer for term recall, so they win.
    """
    filters = dict(
        where_source=where_source,
        where_since=where_since,
        where_until=where_until,
        where_title_like=where_title_like,
        where_file_like=where_file_like,
    )
    keyword = keyword_search(db_path, query, top_k=top_k, **filters)
    semantic = search(
        db_path, query, embed_fn, top_k=top_k,
        confidence_threshold=confidence_threshold, **filters,
    )
    kw_ids = {r["chunk_id"] for r in keyword}
    semantic = [r for r in semantic if r["chunk_id"] not in kw_ids]
    return {"keyword": keyword, "semantic": semantic}


def get_code_meta(db_path: str, session_id: str) -> dict | None:
    """Return the extracted code metadata for a session, or None.

    Reads the derived ``code_meta`` table (AC2). Returns a dict with
    ``files``/``commands``/``tools`` (lists) and ``error_count`` (int),
    or None when the session has no code metadata (e.g. chat sessions).
    """
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT files_json, commands_json, tools_json, error_count "
            "FROM code_meta WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    import json

    return {
        "files": json.loads(row[0]),
        "commands": json.loads(row[1]),
        "tools": json.loads(row[2]),
        "error_count": row[3],
    }


def get_chunk(db_path: str, chunk_id: str) -> dict | None:
    """Fetch a single chunk row by chunk_id. None if absent."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT chunk_id, session_id, turn_id, role, text, timestamp, source, title "
            "FROM chunks WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "chunk_id": row[0], "session_id": row[1], "turn_id": row[2],
        "role": row[3], "text": row[4], "timestamp": row[5],
        "source": row[6], "title": row[7],
    }


def get_session_turns(db_path: str, session_id: str) -> dict | None:
    """Return a whole session for the full-session display level.

    The seed's hierarchical display is chunk hit → ±N context → full
    session; this backs the last level. Returns
    {session_id, title, source, turns:[{turn_id, role, text, timestamp}]}
    in stored (chronological) order, or None for an unknown session.
    Only non-empty turns are stored, so that's what the reader shows.
    """
    conn = sqlite3.connect(db_path)
    try:
        meta = conn.execute(
            "SELECT title, source FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        rows = conn.execute(
            "SELECT turn_id, role, text, timestamp FROM chunks "
            "WHERE session_id = ? ORDER BY rowid",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()

    if meta is None:
        return None
    return {
        "session_id": session_id,
        "title": meta[0],
        "source": meta[1],
        "turns": [
            {"turn_id": r[0], "role": r[1], "text": r[2], "timestamp": r[3]}
            for r in rows
        ],
    }


def get_session_meta(db_path: str, session_id: str) -> dict | None:
    """Session-level scope signals for the result list and reader header.

    Returns the three signals a user wants before diving into a session:
    total turn count, first/last timestamp (span), and role distribution.
    ``None`` if the session is unknown (mirrors ``get_session_turns``).
    """
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        agg = conn.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM chunks "
            "WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        roles = conn.execute(
            "SELECT role, COUNT(*) FROM chunks WHERE session_id = ? GROUP BY role",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return {
        "turns": agg[0] or 0,
        "first_ts": agg[1],
        "last_ts": agg[2],
        "by_role": {r[0]: r[1] for r in roles},
    }


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
