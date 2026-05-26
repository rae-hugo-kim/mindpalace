"""Tests for mindpalace.storage."""
import sqlite3

from mindpalace.storage import count_chunks, init_db, store_session


def _fake_embed(text: str) -> list[float]:
    """Cheap stand-in embedding used to keep storage tests fast and deterministic."""
    return [float(len(text)) / 1000.0] * 384


def _sample_session_with_secret() -> dict:
    return {
        "session_id": "s1",
        "title": "Test session",
        "turns": [
            {
                "turn_id": "t1",
                "role": "user",
                "text": "Use key sk-fakekey1234567 to call the API",
                "timestamp": "2026-05-01T00:00:00Z",
                "parent_id": None,
            },
            {
                "turn_id": "t2",
                "role": "assistant",
                "text": "Sure, here is the answer.",
                "timestamp": "2026-05-01T00:00:05Z",
                "parent_id": "t1",
            },
        ],
        "extra": {"cwd": "/proj", "git_branch": "main"},
    }


def test_init_db_idempotent(tmp_path):
    """T8 (RED): init_db creates schema and can be called twice without error."""
    db = str(tmp_path / "test.db")
    init_db(db)
    init_db(db)  # second call must not raise
    assert count_chunks(db) == 0


def test_store_session_basic(tmp_path):
    """T8 (RED): session + masked chunks + vectors persisted; raw secret removed."""
    db = str(tmp_path / "test.db")
    init_db(db)

    result = store_session(db, _sample_session_with_secret(), source="claude-code", embed_fn=_fake_embed)

    assert result["sessions_inserted"] == 1
    assert result["chunks_inserted"] == 2
    assert result["dedup_skipped"] == 0
    assert count_chunks(db) == 2

    # masking applied at the store boundary — raw chunk text must not contain the secret
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT text FROM chunks WHERE chunk_id='s1:t1'").fetchone()
    conn.close()
    assert row is not None
    assert "sk-fakekey1234567" not in row[0]
    assert "[MASKED]" in row[0]


def test_store_session_dedup_on_reimport(tmp_path):
    """E3 (RED): re-importing the same session does not duplicate sessions or chunks."""
    db = str(tmp_path / "test.db")
    init_db(db)
    session = _sample_session_with_secret()

    first = store_session(db, session, source="claude-code", embed_fn=_fake_embed)
    second = store_session(db, session, source="claude-code", embed_fn=_fake_embed)

    assert first["chunks_inserted"] == 2
    assert second["chunks_inserted"] == 0
    assert second["dedup_skipped"] == 2
    assert count_chunks(db) == 2


def test_store_session_skips_empty_text_turns(tmp_path):
    """T12 (RED): turns whose text is empty / whitespace-only are not stored.

    Mirrors the chunker policy: dry-run #1 showed 12% of Code turns
    have empty text (tool placeholders); storing them wastes the embed
    call, the chunk row, and the vector slot.
    """
    db = str(tmp_path / "test.db")
    init_db(db)
    session = {
        "session_id": "s9",
        "title": "T",
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "real one", "timestamp": "", "parent_id": None},
            {"turn_id": "t2", "role": "assistant", "text": "", "timestamp": "", "parent_id": None},
            {"turn_id": "t3", "role": "user", "text": "   \n\t  ", "timestamp": "", "parent_id": None},
        ],
        "extra": {},
    }

    result = store_session(db, session, source="claude-code", embed_fn=_fake_embed)

    assert result["chunks_inserted"] == 1
    assert result["dedup_skipped"] == 0
    assert count_chunks(db) == 1


def test_store_session_records_source_and_metadata(tmp_path):
    """T8: source + session-level metadata (title, extra) are retrievable."""
    db = str(tmp_path / "test.db")
    init_db(db)
    store_session(db, _sample_session_with_secret(), source="claude-code", embed_fn=_fake_embed)

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT source, title FROM sessions WHERE session_id='s1'"
    ).fetchone()
    conn.close()
    assert row == ("claude-code", "Test session")
