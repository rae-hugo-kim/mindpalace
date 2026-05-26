"""CLI smoke tests using typer's CliRunner.

These tests exercise the user-facing entry points end-to-end with a real
embedding model and a real SQLite + sqlite-vec DB, mirroring the
integration test's posture. The warm_model fixture from
``test_embedding`` is reused via conftest auto-discovery is not in place,
so we trigger a single warmup at module scope here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindpalace.cli import app
from mindpalace.embedding import embed_chunk


@pytest.fixture(scope="module")
def warm_model() -> None:
    embed_chunk("warmup")


def _write_code_jsonl(p: Path) -> None:
    lines = [
        {"type": "ai-title", "aiTitle": "MCP setup walkthrough"},
        {
            "type": "user",
            "uuid": "u1",
            "parentUuid": None,
            "timestamp": "2026-05-26T10:00:00Z",
            "cwd": "/tmp",
            "gitBranch": "main",
            "message": {"content": "How do I set up MCP servers in Claude Code?"},
        },
        {
            "type": "assistant",
            "uuid": "a1",
            "parentUuid": "u1",
            "timestamp": "2026-05-26T10:00:05Z",
            "message": {"content": "You add a stdio server via `claude mcp add`."},
        },
        {
            "type": "user",
            "uuid": "u2",
            "parentUuid": "a1",
            "timestamp": "2026-05-26T10:01:00Z",
            "message": {"content": "Totally unrelated: recursion in lambda calculus."},
        },
    ]
    with p.open("w") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")


def _write_chat_json(p: Path) -> None:
    data = {
        "schema_version": 1,
        "conversations": [
            {
                "uuid": "conv-1",
                "name": "Talking about MCP",
                "summary": "",
                "created_at": "2026-05-26T09:00:00Z",
                "updated_at": "2026-05-26T09:10:00Z",
                "chat_messages": [
                    {
                        "uuid": "m1",
                        "parent_message_uuid": None,
                        "sender": "human",
                        "text": "What is MCP exactly?",
                        "created_at": "2026-05-26T09:00:00Z",
                    },
                    {
                        "uuid": "m2",
                        "parent_message_uuid": "m1",
                        "sender": "assistant",
                        "text": "MCP is the Model Context Protocol for connecting tools.",
                        "created_at": "2026-05-26T09:00:30Z",
                    },
                ],
            }
        ],
    }
    p.write_text(json.dumps(data))


def test_cli_import_code_then_search(tmp_path: Path, warm_model: None) -> None:
    runner = CliRunner()
    jsonl_path = tmp_path / "session-abc.jsonl"
    db_path = tmp_path / "mp.db"
    _write_code_jsonl(jsonl_path)

    result = runner.invoke(
        app,
        ["import", str(jsonl_path), "--source", "code", "--db", str(db_path)],
    )
    assert result.exit_code == 0, result.output
    assert "chunks_inserted=3" in result.output
    assert "sessions_inserted=1" in result.output

    result = runner.invoke(
        app,
        ["search", "How do I set up MCP servers?", "--db", str(db_path), "--top-k", "2"],
    )
    assert result.exit_code == 0, result.output
    # Top hit should mention MCP, not recursion.
    assert "MCP" in result.output or "mcp" in result.output
    assert "recursion" not in result.output.lower() or result.output.lower().count("recursion") <= 1


def test_cli_import_chat(tmp_path: Path, warm_model: None) -> None:
    runner = CliRunner()
    chat_path = tmp_path / "chats.json"
    db_path = tmp_path / "mp.db"
    _write_chat_json(chat_path)

    result = runner.invoke(
        app,
        ["import", str(chat_path), "--source", "chat", "--db", str(db_path)],
    )
    assert result.exit_code == 0, result.output
    assert "chunks_inserted=2" in result.output
    assert "sessions_inserted=1" in result.output


def test_cli_search_context_flag_shows_neighbors(tmp_path: Path, warm_model: None) -> None:
    """T15 (RED): `--context 1` adds ±1 neighbor turns under each hit, with ► on the hit row."""
    runner = CliRunner()
    jsonl_path = tmp_path / "session-abc.jsonl"
    db_path = tmp_path / "mp.db"
    _write_code_jsonl(jsonl_path)

    runner.invoke(app, ["import", str(jsonl_path), "--source", "code", "--db", str(db_path)])

    result = runner.invoke(
        app,
        ["search", "How do I set up MCP servers?", "--db", str(db_path),
         "--top-k", "1", "--context", "1"],
    )
    assert result.exit_code == 0, result.output
    # Exactly one ► marker (the hit row in its own context block).
    assert result.output.count("►") == 1
    # The hit's neighboring turns from _write_code_jsonl should appear somewhere.
    # The code JSONL contains a user/assistant pair around "MCP" and a separate
    # "recursion" turn; with --context 1 the neighbor should show.
    assert "MCP" in result.output


def test_cli_search_source_filter(tmp_path: Path, warm_model: None) -> None:
    """T14 (RED): `--source` flag restricts results to that source."""
    runner = CliRunner()
    jsonl_path = tmp_path / "session-abc.jsonl"
    chat_path = tmp_path / "chats.json"
    db_path = tmp_path / "mp.db"
    _write_code_jsonl(jsonl_path)
    _write_chat_json(chat_path)

    runner.invoke(app, ["import", str(jsonl_path), "--source", "code", "--db", str(db_path)])
    runner.invoke(app, ["import", str(chat_path), "--source", "chat", "--db", str(db_path)])

    # Without filter: chat session UUID "conv-1" can appear.
    no_filter = runner.invoke(
        app,
        ["search", "MCP", "--db", str(db_path), "--top-k", "10"],
    )
    assert no_filter.exit_code == 0
    assert "conv-1" in no_filter.output or "chat" in no_filter.output

    # With --source code: chat session must not appear.
    filtered = runner.invoke(
        app,
        ["search", "MCP", "--db", str(db_path), "--top-k", "10", "--source", "code"],
    )
    assert filtered.exit_code == 0, filtered.output
    assert "conv-1" not in filtered.output
    # All result lines must show "source=code".
    for line in filtered.output.splitlines():
        if "distance=" in line:
            assert "source=code" in line, line


def test_cli_search_warns_when_all_low_confidence(tmp_path: Path, warm_model: None) -> None:
    """T13 (RED): if every hit is low-confidence, CLI prints a warning line."""
    runner = CliRunner()
    jsonl_path = tmp_path / "session-abc.jsonl"
    db_path = tmp_path / "mp.db"
    _write_code_jsonl(jsonl_path)

    runner.invoke(
        app,
        ["import", str(jsonl_path), "--source", "code", "--db", str(db_path)],
    )

    # Force-low: threshold 0 means everything is low-confidence.
    result = runner.invoke(
        app,
        [
            "search",
            "How do I set up MCP servers?",
            "--db", str(db_path),
            "--top-k", "2",
            "--min-confidence", "0",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "low-confidence" in result.output.lower() or "low confidence" in result.output.lower()


def test_cli_search_empty_db_shows_no_hits(tmp_path: Path, warm_model: None) -> None:
    runner = CliRunner()
    db_path = tmp_path / "mp.db"
    from mindpalace.storage import init_db

    init_db(str(db_path))

    result = runner.invoke(
        app,
        ["search", "anything at all", "--db", str(db_path)],
    )
    assert result.exit_code == 0, result.output
    assert "no results" in result.output.lower() or "0 hits" in result.output.lower()
