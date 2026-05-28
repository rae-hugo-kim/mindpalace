"""Tests for mindpalace.search.

Uses the real sentence-transformers model so the semantic ordering can be
exercised end-to-end. Model is cached after the first run (see test_embedding).
"""
from mindpalace.embedding import embed_chunk
from mindpalace.search import (
    find_neighbors,
    get_chunk_context,
    get_session_meta,
    hybrid_search,
    keyword_search,
    search,
)
from mindpalace.storage import init_db, store_session


def _store_three_chunks(db: str) -> None:
    session = {
        "session_id": "s1",
        "title": "Mixed topics",
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "How do I configure MCP servers in Claude Code?", "timestamp": "T", "parent_id": None},
            {"turn_id": "t2", "role": "assistant", "text": "Set up an entry in your settings file.", "timestamp": "T", "parent_id": "t1"},
            {"turn_id": "t3", "role": "user", "text": "What is recursion in programming?", "timestamp": "T", "parent_id": None},
        ],
        "extra": {},
    }
    store_session(db, session, source="claude-code", embed_fn=embed_chunk)


def test_search_empty_db_zero_hits(tmp_path):
    """E4 (RED): search on an empty DB returns an empty list (no exception)."""
    db = str(tmp_path / "empty.db")
    init_db(db)
    assert search(db, "anything", embed_chunk, top_k=5) == []


def test_search_returns_results_ordered_by_distance(tmp_path):
    """T9 (RED): top-k results returned in ascending distance order."""
    db = str(tmp_path / "ranked.db")
    init_db(db)
    _store_three_chunks(db)

    results = search(db, "MCP setup", embed_chunk, top_k=2)

    assert len(results) == 2
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances)
    # the unrelated "recursion" chunk must not be in top-2 for an MCP query
    assert "s1:t3" not in [r["chunk_id"] for r in results]


def test_search_includes_chunk_metadata(tmp_path):
    """T9 (RED): each result carries chunk_id, session_id, title, role, text, timestamp, distance."""
    db = str(tmp_path / "meta.db")
    init_db(db)
    session = {
        "session_id": "s1",
        "title": "TestTitle",
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "Hello world", "timestamp": "2026-05-01T00:00:00Z", "parent_id": None},
        ],
        "extra": {},
    }
    store_session(db, session, source="claude-code", embed_fn=embed_chunk)

    results = search(db, "Hello world", embed_chunk, top_k=5)
    assert len(results) == 1
    r = results[0]
    assert r["chunk_id"] == "s1:t1"
    assert r["session_id"] == "s1"
    assert r["title"] == "TestTitle"
    assert r["role"] == "user"
    assert r["text"] == "Hello world"
    assert r["timestamp"] == "2026-05-01T00:00:00Z"
    assert r["source"] == "claude-code"
    assert isinstance(r["distance"], float)


def test_search_marks_low_confidence_when_distance_above_threshold(tmp_path):
    """T13 (RED): each result carries ``low_confidence`` flagged by ``confidence_threshold``.

    dry-run #1 showed sqlite-vec never returns fewer than k rows on a
    populated DB, even for obviously irrelevant queries — so the UX has
    to label results, not just count them.
    """
    db = str(tmp_path / "conf.db")
    init_db(db)
    _store_three_chunks(db)

    # Threshold=0 → every (non-zero) distance is "above" → all low-confidence.
    low = search(db, "MCP setup", embed_chunk, top_k=3, confidence_threshold=0.0)
    assert len(low) == 3
    assert all(r["low_confidence"] is True for r in low)

    # Threshold=huge → nothing crosses it → no flags.
    hi = search(db, "MCP setup", embed_chunk, top_k=3, confidence_threshold=1e6)
    assert len(hi) == 3
    assert all(r["low_confidence"] is False for r in hi)


def test_search_default_confidence_threshold_filters_irrelevant(tmp_path):
    """T13 (RED): a real "obviously irrelevant" query gets flagged low_confidence.

    Verifies the v0 default threshold is tight enough to mark the
    unrelated recursion chunk as low-confidence for an off-topic query.
    """
    db = str(tmp_path / "default-conf.db")
    init_db(db)
    _store_three_chunks(db)

    # English-only, deliberately off-topic vs the stored 3 turns.
    results = search(db, "the boiling point of water", embed_chunk, top_k=3)
    assert len(results) == 3
    # At least one must be flagged low_confidence — they're all off-topic.
    assert any(r["low_confidence"] is True for r in results)


def test_search_filters_by_source(tmp_path):
    """T14 (RED): ``where_source`` restricts hits to a single source.

    Stores one chunk per source and queries with an explicit filter for
    each. dry-run #1 showed chat:code = 9:1 in the live corpus, so
    source filtering is the most-needed meta filter.
    """
    db = str(tmp_path / "src-filter.db")
    init_db(db)
    code_session = {
        "session_id": "code-1",
        "title": "Code session",
        "turns": [
            {"turn_id": "c1", "role": "user", "text": "Configure MCP server config", "timestamp": "T", "parent_id": None},
        ],
        "extra": {},
    }
    chat_session = {
        "session_id": "chat-1",
        "title": "Chat session",
        "turns": [
            {"turn_id": "m1", "role": "user", "text": "Configure MCP server config", "timestamp": "T", "parent_id": None},
        ],
        "extra": {},
    }
    store_session(db, code_session, source="code", embed_fn=embed_chunk)
    store_session(db, chat_session, source="chat", embed_fn=embed_chunk)

    code_only = search(db, "MCP server config", embed_chunk, top_k=5, where_source="code")
    assert len(code_only) == 1
    assert code_only[0]["source"] == "code"
    assert code_only[0]["session_id"] == "code-1"

    chat_only = search(db, "MCP server config", embed_chunk, top_k=5, where_source="chat")
    assert len(chat_only) == 1
    assert chat_only[0]["source"] == "chat"
    assert chat_only[0]["session_id"] == "chat-1"

    both = search(db, "MCP server config", embed_chunk, top_k=5)
    assert {r["source"] for r in both} == {"code", "chat"}


def _seven_turn_session(session_id: str = "s7") -> dict:
    return {
        "session_id": session_id,
        "title": "Long session",
        "turns": [
            {"turn_id": f"t{i}", "role": "user" if i % 2 == 0 else "assistant",
             "text": f"turn {i} content", "timestamp": f"2026-05-01T00:0{i}:00Z", "parent_id": None}
            for i in range(7)
        ],
        "extra": {},
    }


def test_get_chunk_context_returns_neighbors_around_hit(tmp_path):
    """T15 (RED): get_chunk_context returns the hit turn plus ±window neighbors.

    AC4 — "검색 hit 청크와 해당 세션의 전후 컨텍스트(기본 청크 ±3, 파라미터)를 같이 표시할 수 있다".
    """
    db = str(tmp_path / "ctx.db")
    init_db(db)
    store_session(db, _seven_turn_session(), source="claude-code", embed_fn=embed_chunk)

    context = get_chunk_context(db, session_id="s7", turn_id="t3", window=2)

    # Hit at index 3, window=2 → expect turns 1..5 inclusive (5 entries).
    assert [c["turn_id"] for c in context] == ["t1", "t2", "t3", "t4", "t5"]
    # Exactly one row is the hit.
    hits = [c for c in context if c["is_hit"]]
    assert len(hits) == 1
    assert hits[0]["turn_id"] == "t3"


def test_get_chunk_context_clamps_at_session_boundaries(tmp_path):
    """T15 (RED): window does not wrap past start/end of the session."""
    db = str(tmp_path / "ctx-clamp.db")
    init_db(db)
    store_session(db, _seven_turn_session(), source="claude-code", embed_fn=embed_chunk)

    head = get_chunk_context(db, session_id="s7", turn_id="t0", window=3)
    assert [c["turn_id"] for c in head] == ["t0", "t1", "t2", "t3"]

    tail = get_chunk_context(db, session_id="s7", turn_id="t6", window=3)
    assert [c["turn_id"] for c in tail] == ["t3", "t4", "t5", "t6"]


def _make_dated_session(session_id: str, day: str, text: str = "anchor") -> dict:
    """Single-turn session whose only turn carries the given ISO date."""
    return {
        "session_id": session_id,
        "title": f"Session {session_id}",
        "turns": [
            {"turn_id": "t1", "role": "user", "text": text,
             "timestamp": f"{day}T12:00:00Z", "parent_id": None},
        ],
        "extra": {},
    }


def test_find_neighbors_returns_opposite_source_within_window(tmp_path):
    """T18 (RED): given a chat session, find_neighbors lists code sessions
    whose timestamps fall within ±window_days, and vice versa.

    Models the seed AC6 weak link: 학습(chat) ↔ 작업(code) within ±3 days.
    """
    db = str(tmp_path / "neigh.db")
    init_db(db)
    # chat "A" on day 0, code "B" on day +1 (in window), code "C" on day +30 (out).
    store_session(db, _make_dated_session("A", "2026-05-26"), source="chat", embed_fn=embed_chunk)
    store_session(db, _make_dated_session("B", "2026-05-27"), source="code", embed_fn=embed_chunk)
    store_session(db, _make_dated_session("C", "2026-06-30"), source="code", embed_fn=embed_chunk)

    neighbors = find_neighbors(db, session_id="A", window_days=3)
    assert [n["session_id"] for n in neighbors] == ["B"]
    n = neighbors[0]
    assert n["source"] == "code"
    assert n["title"] == "Session B"
    assert "anchor_timestamp" in n
    assert "time_delta_days" in n
    # +1 day from anchor
    assert abs(n["time_delta_days"] - 1.0) < 0.01


def test_find_neighbors_excludes_same_source(tmp_path):
    """T18 (RED): same-source sessions are not returned (chat≠code only)."""
    db = str(tmp_path / "neigh-same.db")
    init_db(db)
    store_session(db, _make_dated_session("A", "2026-05-26"), source="chat", embed_fn=embed_chunk)
    # Another chat session 1 day later — same source as A, must be excluded.
    store_session(db, _make_dated_session("X", "2026-05-27"), source="chat", embed_fn=embed_chunk)

    assert find_neighbors(db, session_id="A", window_days=3) == []


def test_find_neighbors_unknown_session_returns_empty(tmp_path):
    """T18 (RED): no matching session_id yields an empty list, not an error."""
    db = str(tmp_path / "neigh-missing.db")
    init_db(db)
    store_session(db, _make_dated_session("A", "2026-05-26"), source="chat", embed_fn=embed_chunk)
    assert find_neighbors(db, session_id="no-such", window_days=3) == []


def test_get_chunk_context_unknown_turn_returns_empty(tmp_path):
    """T15 (RED): unknown turn_id yields an empty list (no exception)."""
    db = str(tmp_path / "ctx-missing.db")
    init_db(db)
    store_session(db, _seven_turn_session(), source="claude-code", embed_fn=embed_chunk)

    assert get_chunk_context(db, session_id="s7", turn_id="nope") == []
    assert get_chunk_context(db, session_id="no-such-session", turn_id="t0") == []


def test_search_filters_by_time_range(tmp_path):
    """T16 (RED, AC5): where_since/where_until bound results by chunk timestamp."""
    db = str(tmp_path / "time-filter.db")
    init_db(db)
    store_session(db, _make_dated_session("old", "2026-01-01", "MCP config"), source="code", embed_fn=embed_chunk)
    store_session(db, _make_dated_session("mid", "2026-05-15", "MCP config"), source="code", embed_fn=embed_chunk)
    store_session(db, _make_dated_session("new", "2026-09-01", "MCP config"), source="code", embed_fn=embed_chunk)

    # Window May..June → only the "mid" session.
    windowed = search(db, "MCP config", embed_chunk, top_k=10,
                      where_since="2026-05-01", where_until="2026-06-01")
    assert {r["session_id"] for r in windowed} == {"mid"}

    # since only.
    since_only = search(db, "MCP config", embed_chunk, top_k=10, where_since="2026-05-01")
    assert {r["session_id"] for r in since_only} == {"mid", "new"}


def test_search_filters_by_title_like(tmp_path):
    """T16 (RED, AC5): where_title_like is a substring (case-insensitive) match."""
    db = str(tmp_path / "title-filter.db")
    init_db(db)
    store_session(
        db,
        {"session_id": "kv", "title": "Knowledge Vault design", "extra": {},
         "turns": [{"turn_id": "t1", "role": "user", "text": "store and search", "timestamp": "2026-05-01T00:00:00Z", "parent_id": None}]},
        source="code", embed_fn=embed_chunk,
    )
    store_session(
        db,
        {"session_id": "diet", "title": "레그프레스 운동 루틴", "extra": {},
         "turns": [{"turn_id": "t1", "role": "user", "text": "store and search", "timestamp": "2026-05-01T00:00:00Z", "parent_id": None}]},
        source="chat", embed_fn=embed_chunk,
    )

    res = search(db, "store and search", embed_chunk, top_k=10, where_title_like="vault")
    assert {r["session_id"] for r in res} == {"kv"}


def test_search_filters_by_file_like(tmp_path):
    """T20 (RED, AC5/AC2): where_file_like restricts hits to code sessions
    whose extracted code_meta.files contain the substring.

    Completes the "파일 path" arm of AC5, made possible by AC2 metadata
    extraction.
    """
    db = str(tmp_path / "file-filter.db")
    init_db(db)
    search_sess = {
        "session_id": "touches-search",
        "title": "Edited search",
        "turns": [{"turn_id": "t1", "role": "user", "text": "refactor the ranking",
                   "timestamp": "2026-05-01T00:00:00Z", "parent_id": None}],
        "extra": {},
        "code_meta": {"files": ["/proj/src/search.py"], "commands": [],
                      "tools": ["Edit"], "error_count": 0},
    }
    storage_sess = {
        "session_id": "touches-storage",
        "title": "Edited storage",
        "turns": [{"turn_id": "t1", "role": "user", "text": "refactor the ranking",
                   "timestamp": "2026-05-01T00:00:00Z", "parent_id": None}],
        "extra": {},
        "code_meta": {"files": ["/proj/src/storage.py"], "commands": [],
                      "tools": ["Edit"], "error_count": 0},
    }
    store_session(db, search_sess, source="code", embed_fn=embed_chunk)
    store_session(db, storage_sess, source="code", embed_fn=embed_chunk)

    res = search(db, "refactor the ranking", embed_chunk, top_k=10,
                 where_file_like="search.py")
    assert {r["session_id"] for r in res} == {"touches-search"}


def test_search_logs_latency(tmp_path, caplog):
    """T21 (RED, AC15): each search emits a latency log record on the
    mindpalace.search logger with a latency_ms field and the hit count."""
    import logging

    db = str(tmp_path / "latency.db")
    init_db(db)
    _store_three_chunks(db)

    with caplog.at_level(logging.INFO, logger="mindpalace.search"):
        search(db, "MCP setup", embed_chunk, top_k=2)

    records = [r for r in caplog.records if r.name == "mindpalace.search"]
    assert records, "expected a mindpalace.search log record"
    msg = records[-1].getMessage()
    assert "latency_ms=" in msg
    assert "hits=2" in msg


def _store_keyword_corpus(db: str) -> None:
    """A rare proper noun ('조플렉신') that the embedding model represents
    poorly, plus unrelated content that semantic search prefers."""
    store_session(db, {
        "session_id": "drug", "title": "조플렉신 부작용", "extra": {},
        "turns": [{"turn_id": "t1", "role": "user",
                   "text": "조플렉신 5mg 맞고 설사가 심한데 정상인가요?",
                   "timestamp": "2026-05-10T00:00:00Z", "parent_id": None}],
    }, source="chat", embed_fn=embed_chunk)
    store_session(db, {
        "session_id": "mcp", "title": "MCP setup", "extra": {},
        "turns": [{"turn_id": "t1", "role": "user",
                   "text": "How do I configure MCP servers in Claude Code?",
                   "timestamp": "2026-05-11T00:00:00Z", "parent_id": None}],
    }, source="code", embed_fn=embed_chunk)


def test_keyword_search_finds_exact_substring(tmp_path):
    """T29 (RED): keyword_search does a substring match the embedding misses.

    '조플렉신' (a drug brand name) is a rare proper noun the multilingual
    model can't represent, so semantic search ranks it below noise; a LIKE
    match nails it. Results carry match='keyword'.
    """
    db = str(tmp_path / "kw.db")
    init_db(db)
    _store_keyword_corpus(db)

    res = keyword_search(db, "조플렉신", top_k=10)
    assert [r["session_id"] for r in res] == ["drug"]
    assert res[0]["match"] == "keyword"
    assert res[0]["distance"] is None  # keyword hits have no vector distance
    # (semantic search buries this rare proper noun at corpus scale — see the
    # real-vault investigation; not asserted here since a 2-chunk corpus is
    # too small to reproduce the dilution.)


def test_hybrid_search_merges_keyword_first_deduped(tmp_path):
    """T29 (RED): hybrid_search returns {keyword, semantic}; semantic excludes
    chunk_ids already shown as keyword matches."""
    db = str(tmp_path / "hyb.db")
    init_db(db)
    _store_keyword_corpus(db)

    out = hybrid_search(db, "조플렉신", embed_chunk, top_k=5)
    assert "keyword" in out and "semantic" in out
    kw_ids = {r["chunk_id"] for r in out["keyword"]}
    assert "drug:t1" in kw_ids
    # no overlap between the two lists
    sem_ids = {r["chunk_id"] for r in out["semantic"]}
    assert kw_ids.isdisjoint(sem_ids)


def test_keyword_search_respects_source_filter(tmp_path):
    """T29 (RED): keyword_search honors the source filter like semantic does."""
    db = str(tmp_path / "kwsrc.db")
    init_db(db)
    _store_keyword_corpus(db)
    # 'MCP' substring exists only in the code session
    res = keyword_search(db, "MCP", top_k=10, where_source="chat")
    assert res == []


def test_search_respects_top_k(tmp_path):
    """T9: top_k caps the number of results returned."""
    db = str(tmp_path / "topk.db")
    init_db(db)
    _store_three_chunks(db)

    assert len(search(db, "anything", embed_chunk, top_k=1)) == 1
    assert len(search(db, "anything", embed_chunk, top_k=10)) == 3


def test_keyword_search_trims_surrounding_whitespace(tmp_path):
    """T35 (RED): a query with leading/trailing whitespace must still find the
    same chunks as the trimmed query. Real users paste/type queries with stray
    spaces; literal `LIKE '%  q  %'` would silently miss the substring.
    """
    db = str(tmp_path / "kwtrim.db")
    init_db(db)
    _store_keyword_corpus(db)

    res = keyword_search(db, "  조플렉신  ", top_k=10)
    assert [r["session_id"] for r in res] == ["drug"]


def test_keyword_search_empty_query_returns_no_results(tmp_path):
    """T35 (RED): an empty or whitespace-only query must not run a wildcard
    ``%%`` match that returns the entire corpus.
    """
    db = str(tmp_path / "kwempty.db")
    init_db(db)
    _store_keyword_corpus(db)

    assert keyword_search(db, "", top_k=10) == []
    assert keyword_search(db, "   ", top_k=10) == []
    # hybrid_search should also short-circuit the keyword side
    out = hybrid_search(db, "   ", embed_chunk, top_k=5)
    assert out["keyword"] == []


def test_get_session_meta_returns_size_span_and_role_counts(tmp_path):
    """T36 (RED): get_session_meta gives the three signals a hit/session reader
    needs *before* opening the session — turn count, time span (first/last
    timestamp), and role distribution. Lets the user judge depth from the
    search result alone instead of clicking into each session.
    """
    db = str(tmp_path / "smeta.db")
    init_db(db)
    store_session(db, {
        "session_id": "deep", "title": "long thread", "extra": {},
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "q1",
             "timestamp": "2026-05-10T09:00:00Z", "parent_id": None},
            {"turn_id": "t2", "role": "assistant", "text": "a1",
             "timestamp": "2026-05-10T09:01:00Z", "parent_id": "t1"},
            {"turn_id": "t3", "role": "user", "text": "q2",
             "timestamp": "2026-05-12T14:00:00Z", "parent_id": None},
            {"turn_id": "t4", "role": "assistant", "text": "a2",
             "timestamp": "2026-05-12T14:05:00Z", "parent_id": "t3"},
        ],
    }, source="chat", embed_fn=embed_chunk)

    meta = get_session_meta(db, "deep")
    assert meta is not None
    assert meta["turns"] == 4
    assert meta["first_ts"] == "2026-05-10T09:00:00Z"
    assert meta["last_ts"] == "2026-05-12T14:05:00Z"
    assert meta["by_role"] == {"user": 2, "assistant": 2}


def test_get_session_meta_missing_session_returns_none(tmp_path):
    """T36 (RED): unknown session_id returns None (mirrors get_session_turns)."""
    db = str(tmp_path / "smeta_miss.db")
    init_db(db)
    assert get_session_meta(db, "nope") is None


def test_keyword_search_is_case_insensitive_for_non_ascii(tmp_path):
    """T35 (RED): SQLite default LIKE folds only ASCII A–Z; non-ASCII
    characters (e.g. accented Latin like 'CAFÉ') stay case-sensitive. Real
    chat/code text mixes cases, so 'café' should also find 'CAFÉ' chunks.
    """
    db = str(tmp_path / "kwcase.db")
    init_db(db)
    store_session(db, {
        "session_id": "cafe", "title": "café notes", "extra": {},
        "turns": [{"turn_id": "t1", "role": "user",
                   "text": "Best CAFÉ in Seoul for studying?",
                   "timestamp": "2026-05-15T00:00:00Z", "parent_id": None}],
    }, source="chat", embed_fn=embed_chunk)

    res = keyword_search(db, "café", top_k=10)
    assert [r["session_id"] for r in res] == ["cafe"]
