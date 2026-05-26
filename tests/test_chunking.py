"""Tests for mindpalace.chunking."""
from mindpalace.chunking import chunk_session


def test_chunk_session_basic():
    """T6 (RED): 1 turn = 1 chunk; chunk carries session + per-turn metadata."""
    session = {
        "session_id": "s1",
        "title": "Test session",
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "Hi", "timestamp": "2026-05-01T00:00:00Z", "parent_id": None},
            {"turn_id": "t2", "role": "assistant", "text": "Hello", "timestamp": "2026-05-01T00:00:05Z", "parent_id": "t1"},
        ],
        "extra": {"cwd": "/proj", "git_branch": "main"},
    }
    chunks = chunk_session(session, source="claude-code")

    assert len(chunks) == 2

    c0 = chunks[0]
    assert c0["chunk_id"] == "s1:t1"
    assert c0["session_id"] == "s1"
    assert c0["turn_id"] == "t1"
    assert c0["source"] == "claude-code"
    assert c0["title"] == "Test session"
    assert c0["role"] == "user"
    assert c0["text"] == "Hi"
    assert c0["timestamp"] == "2026-05-01T00:00:00Z"
    assert c0["parent_id"] is None
    # session-level extra is propagated as-is
    assert c0["extra"] == {"cwd": "/proj", "git_branch": "main"}

    c1 = chunks[1]
    assert c1["chunk_id"] == "s1:t2"
    assert c1["role"] == "assistant"
    assert c1["parent_id"] == "t1"


def test_chunk_session_empty_turns():
    """T6: session with no turns -> empty chunk list."""
    session = {"session_id": "s2", "title": None, "turns": [], "extra": {}}
    assert chunk_session(session, source="claude-chat") == []


def test_chunk_session_source_value_threaded():
    """T6: source argument is propagated unchanged to every chunk."""
    session = {
        "session_id": "s3",
        "title": "Chat title",
        "turns": [
            {"turn_id": "m1", "role": "user", "text": "Q", "timestamp": "T", "parent_id": None},
        ],
        "extra": {"summary": "user summary"},
    }
    chunks = chunk_session(session, source="claude-chat")
    assert chunks[0]["source"] == "claude-chat"
    # extra is propagated regardless of source-specific keys
    assert chunks[0]["extra"]["summary"] == "user summary"
