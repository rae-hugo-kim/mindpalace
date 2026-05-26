"""Walking skeleton end-to-end integration test (AC8).

The whole pipeline runs against the real model and a real SQLite DB:
  fixture JSONL -> parse -> store (mask + chunk + embed) -> search.
"""
import sqlite3

from mindpalace.embedding import embed_chunk
from mindpalace.parsing import parse_claude_code_jsonl
from mindpalace.search import search
from mindpalace.storage import init_db, store_session


def test_walking_skeleton_e2e(tmp_path):
    """AC8: import -> mask -> embed -> search round-trip on a fixture JSONL."""
    # 1) Fixture: a small Claude Code JSONL with one secret-bearing turn.
    jsonl = tmp_path / "session-abc.jsonl"
    lines = [
        '{"type":"ai-title","aiTitle":"MCP setup help","sessionId":"sess-1"}',
        '{"type":"user","sessionId":"sess-1","uuid":"t1","parentUuid":null,'
        '"timestamp":"2026-05-01T00:00:00Z",'
        '"message":{"role":"user","content":"My key is sk-fakekey1234567 — help me configure MCP servers"},'
        '"cwd":"/proj","gitBranch":"main"}',
        '{"type":"assistant","sessionId":"sess-1","uuid":"t2","parentUuid":"t1",'
        '"timestamp":"2026-05-01T00:00:05Z",'
        '"message":{"role":"assistant","content":[{"type":"text","text":"Edit your settings file to add the MCP server entry."}]},'
        '"cwd":"/proj","gitBranch":"main"}',
        '{"type":"user","sessionId":"sess-1","uuid":"t3","parentUuid":"t2",'
        '"timestamp":"2026-05-01T00:01:00Z",'
        '"message":{"role":"user","content":"Unrelated: what is recursion in programming?"},'
        '"cwd":"/proj","gitBranch":"main"}',
    ]
    jsonl.write_text("\n".join(lines))

    # 2) Parse.
    session = parse_claude_code_jsonl(str(jsonl))
    assert session["title"] == "MCP setup help"
    assert len(session["turns"]) == 3

    # 3) Store (masking + embedding happen inside).
    db = str(tmp_path / "vault.db")
    init_db(db)
    counts = store_session(db, session, source="claude-code", embed_fn=embed_chunk)
    assert counts["sessions_inserted"] == 1
    assert counts["chunks_inserted"] == 3

    # 4) Verify masking applied at the store boundary — no plain secret in DB.
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("SELECT text FROM chunks").fetchall()
    finally:
        conn.close()
    persisted_text = " ".join(r[0] for r in rows)
    assert "sk-fakekey1234567" not in persisted_text
    assert "[MASKED]" in persisted_text

    # 5) Search — semantically related turns must outrank the unrelated one.
    results = search(db, "How do I set up MCP?", embed_chunk, top_k=2)
    assert len(results) == 2

    top_ids = [r["chunk_id"] for r in results]
    # the "recursion" turn is irrelevant to MCP and must not be in top-2
    assert "session-abc:t3" not in top_ids

    # 6) Result rows carry full chunk metadata for downstream UI/CLI.
    for r in results:
        assert {"chunk_id", "session_id", "title", "role", "text", "timestamp", "source", "distance"} <= r.keys()
        assert r["title"] == "MCP setup help"
        assert r["source"] == "claude-code"
