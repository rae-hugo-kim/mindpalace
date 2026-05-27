"""Tests for mindpalace.storage."""
import json
import sqlite3

import pytest

from mindpalace.storage import (
    _connect,
    count_chunks,
    init_db,
    reindex_vectors,
    store_session,
)


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


def test_connect_enforces_foreign_keys(tmp_path):
    """T25 (RED): connections enable foreign-key enforcement, so a chunk
    referencing a non-existent session is rejected (referential integrity)."""
    db = str(tmp_path / "fk.db")
    init_db(db)

    conn = _connect(db)
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO chunks "
                "(chunk_id, session_id, turn_id, source, title, role, text, "
                "timestamp, parent_id, ingested_at) "
                "VALUES ('orphan:t1','no-such-session','t1','code',NULL,'user','x','','',"
                "'2026-05-27T00:00:00Z')",
            )
            conn.commit()
    finally:
        conn.close()


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


def test_store_session_persists_code_meta(tmp_path):
    """T20 (RED, AC2): a session carrying code_meta writes a derived
    code_meta row; commands are masked; reimport is idempotent."""
    db = str(tmp_path / "test.db")
    init_db(db)
    session = {
        "session_id": "cm1",
        "title": "Code session",
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "do the thing",
             "timestamp": "2026-05-01T00:00:00Z", "parent_id": None},
        ],
        "extra": {},
        "code_meta": {
            "files": ["/proj/src/search.py", "/proj/src/storage.py"],
            "commands": ["export TOKEN=sk-fakekey1234567 && run"],
            "tools": ["Bash", "Read"],
            "error_count": 2,
        },
    }

    store_session(db, session, source="code", embed_fn=_fake_embed)

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT files_json, commands_json, tools_json, error_count "
        "FROM code_meta WHERE session_id='cm1'"
    ).fetchone()
    conn.close()
    assert row is not None
    files_json, commands_json, tools_json, error_count = row
    assert json.loads(files_json) == ["/proj/src/search.py", "/proj/src/storage.py"]
    assert json.loads(tools_json) == ["Bash", "Read"]
    assert error_count == 2
    # command secret masked before persistence
    assert "sk-fakekey1234567" not in commands_json
    assert "[MASKED]" in commands_json

    # reimport must not duplicate the code_meta row
    store_session(db, session, source="code", embed_fn=_fake_embed)
    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM code_meta WHERE session_id='cm1'").fetchone()[0]
    conn.close()
    assert n == 1


def test_store_session_without_code_meta_writes_no_row(tmp_path):
    """T20 (RED, AC2): sessions lacking code_meta (e.g. chat) add no
    code_meta row — the table stays code-only."""
    db = str(tmp_path / "test.db")
    init_db(db)
    store_session(db, _sample_session_with_secret(), source="chat", embed_fn=_fake_embed)

    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM code_meta").fetchone()[0]
    conn.close()
    assert n == 0


def test_store_session_counts_masked_chunks(tmp_path):
    """T21 (RED, AC15): result reports how many chunks had a secret masked.

    The sample session has one secret-bearing turn and one clean turn,
    so exactly one chunk should be counted as masked.
    """
    db = str(tmp_path / "test.db")
    init_db(db)

    result = store_session(db, _sample_session_with_secret(), source="code", embed_fn=_fake_embed)

    assert result["masked"] == 1


def test_store_session_counts_embed_failures_and_skips_chunk(tmp_path):
    """T21 (RED, AC15): an embedding failure is counted, logged, and the
    offending chunk is skipped (not stored) so the rest still import.

    Skipping rather than storing a vector-less chunk keeps chunks/chunk_vec
    in sync; the chunk_id is absent so a later reimport retries it.
    """
    db = str(tmp_path / "test.db")
    init_db(db)

    def _flaky_embed(text: str) -> list[float]:
        if "boom" in text:
            raise RuntimeError("embedding backend exploded")
        return _fake_embed(text)

    session = {
        "session_id": "ef1",
        "title": "T",
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "fine one", "timestamp": "", "parent_id": None},
            {"turn_id": "t2", "role": "assistant", "text": "boom goes the embed", "timestamp": "", "parent_id": None},
            {"turn_id": "t3", "role": "user", "text": "also fine", "timestamp": "", "parent_id": None},
        ],
        "extra": {},
    }

    result = store_session(db, session, source="code", embed_fn=_flaky_embed)

    assert result["embed_failures"] == 1
    assert result["chunks_inserted"] == 2  # the two clean turns
    assert count_chunks(db) == 2
    conn = sqlite3.connect(db)
    missing = conn.execute("SELECT COUNT(*) FROM chunks WHERE chunk_id='ef1:t2'").fetchone()[0]
    conn.close()
    assert missing == 0


def test_reindex_vectors_rebuilds_from_raw_chunks(tmp_path):
    """T26 (RED): reindex_vectors rebuilds chunk_vec from chunks.text after
    the vector table is wiped (seed constraint: derived data rebuildable
    from the immutable raw layer). rowids stay aligned so search joins work."""
    db = str(tmp_path / "reindex.db")
    init_db(db)
    store_session(db, _sample_session_with_secret(), source="code", embed_fn=_fake_embed)
    assert count_chunks(db) == 2

    # Simulate a model/schema change: wipe the derived vector index.
    conn = _connect(db)
    try:
        conn.execute("DELETE FROM chunk_vec")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM chunk_vec").fetchone()[0] == 0
    finally:
        conn.close()

    result = reindex_vectors(db, embed_fn=_fake_embed)
    assert result["reindexed"] == 2

    conn = _connect(db)
    try:
        # one vector per chunk, rowids aligned to chunks.rowid
        n_vec = conn.execute("SELECT COUNT(*) FROM chunk_vec").fetchone()[0]
        aligned = conn.execute(
            "SELECT COUNT(*) FROM chunks c JOIN chunk_vec v ON v.rowid = c.rowid"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n_vec == 2
    assert aligned == 2


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
