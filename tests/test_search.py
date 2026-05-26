"""Tests for mindpalace.search.

Uses the real sentence-transformers model so the semantic ordering can be
exercised end-to-end. Model is cached after the first run (see test_embedding).
"""
from mindpalace.embedding import embed_chunk
from mindpalace.search import get_chunk_context, search
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


def test_get_chunk_context_unknown_turn_returns_empty(tmp_path):
    """T15 (RED): unknown turn_id yields an empty list (no exception)."""
    db = str(tmp_path / "ctx-missing.db")
    init_db(db)
    store_session(db, _seven_turn_session(), source="claude-code", embed_fn=embed_chunk)

    assert get_chunk_context(db, session_id="s7", turn_id="nope") == []
    assert get_chunk_context(db, session_id="no-such-session", turn_id="t0") == []


def test_search_respects_top_k(tmp_path):
    """T9: top_k caps the number of results returned."""
    db = str(tmp_path / "topk.db")
    init_db(db)
    _store_three_chunks(db)

    assert len(search(db, "anything", embed_chunk, top_k=1)) == 1
    assert len(search(db, "anything", embed_chunk, top_k=10)) == 3
