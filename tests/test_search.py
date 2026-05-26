"""Tests for mindpalace.search.

Uses the real sentence-transformers model so the semantic ordering can be
exercised end-to-end. Model is cached after the first run (see test_embedding).
"""
from mindpalace.embedding import embed_chunk
from mindpalace.search import search
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


def test_search_respects_top_k(tmp_path):
    """T9: top_k caps the number of results returned."""
    db = str(tmp_path / "topk.db")
    init_db(db)
    _store_three_chunks(db)

    assert len(search(db, "anything", embed_chunk, top_k=1)) == 1
    assert len(search(db, "anything", embed_chunk, top_k=10)) == 3
