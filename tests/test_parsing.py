"""Tests for mindpalace.parsing."""
import json
from collections.abc import Iterator

import pytest

from mindpalace.parsing import (
    parse_chat_json,
    parse_claude_code_jsonl,
    stream_chat_sessions,
)


def test_parse_claude_code_jsonl_basic(tmp_path):
    """T5 (RED): JSONL with ai-title + user + assistant -> session dict + turns."""
    p = tmp_path / "5069e22f-4fbf-4510-a23e-a99333ba6a93.jsonl"
    lines = [
        '{"type":"ai-title","aiTitle":"Check favicon registration status","sessionId":"sess-1"}',
        '{"type":"user","sessionId":"sess-1","uuid":"t1","parentUuid":null,"timestamp":"2026-05-26T10:00:00Z","message":{"role":"user","content":"Hello there"},"cwd":"/home/rae/proj","gitBranch":"main"}',
        '{"type":"assistant","sessionId":"sess-1","uuid":"t2","parentUuid":"t1","timestamp":"2026-05-26T10:00:05Z","message":{"role":"assistant","content":[{"type":"text","text":"Hi!"}]},"cwd":"/home/rae/proj","gitBranch":"main"}',
    ]
    p.write_text("\n".join(lines))

    result = parse_claude_code_jsonl(str(p))

    assert result["session_id"] == "5069e22f-4fbf-4510-a23e-a99333ba6a93"
    assert result["title"] == "Check favicon registration status"
    assert len(result["turns"]) == 2

    t0 = result["turns"][0]
    assert t0["turn_id"] == "t1"
    assert t0["role"] == "user"
    assert t0["text"] == "Hello there"
    assert t0["timestamp"] == "2026-05-26T10:00:00Z"
    assert t0["parent_id"] is None

    t1 = result["turns"][1]
    assert t1["role"] == "assistant"
    assert t1["text"] == "Hi!"
    assert t1["parent_id"] == "t1"

    assert result["extra"]["cwd"] == "/home/rae/proj"
    assert result["extra"]["git_branch"] == "main"


def test_parse_claude_code_jsonl_empty(tmp_path):
    """E1 (regression net): empty JSONL -> session_id from filename, no turns."""
    p = tmp_path / "deadbeef-1234.jsonl"
    p.write_text("")

    result = parse_claude_code_jsonl(str(p))

    assert result["session_id"] == "deadbeef-1234"
    assert result["title"] is None
    assert result["turns"] == []


def test_parse_claude_code_jsonl_skips_non_turn_records(tmp_path):
    """T5 (RED): non-turn record types (attachment/system/permission-mode/file-history-snapshot) do not become turns."""
    p = tmp_path / "abc.jsonl"
    lines = [
        '{"type":"permission-mode","sessionId":"x","permissionMode":"bypass"}',
        '{"type":"attachment","sessionId":"x","uuid":"a1","timestamp":"t","attachment":{"type":"hook","content":"x"}}',
        '{"type":"system","sessionId":"x","uuid":"s1","timestamp":"t","subtype":"stop_hook_summary"}',
        '{"type":"file-history-snapshot","messageId":"m1","snapshot":{},"isSnapshotUpdate":false}',
        '{"type":"user","sessionId":"x","uuid":"u1","parentUuid":null,"timestamp":"t","message":{"role":"user","content":"only this"}}',
    ]
    p.write_text("\n".join(lines))

    result = parse_claude_code_jsonl(str(p))

    assert len(result["turns"]) == 1
    assert result["turns"][0]["text"] == "only this"


def test_parse_claude_code_jsonl_extracts_code_meta(tmp_path):
    """T20 (RED, AC2): tool_use/tool_result blocks yield code_meta
    (files / commands / tools / error_count) aggregated per session.

    Code metadata lives in tool_use blocks (Bash command, Read/Edit/Write
    file_path) and tool_result blocks (is_error), all of which the text
    flattener discards. AC2 requires them indexed.
    """
    p = tmp_path / "sess.jsonl"
    lines = [
        # assistant turn carrying two tool_use blocks
        '{"type":"assistant","uuid":"a1","parentUuid":null,"timestamp":"t",'
        '"message":{"role":"assistant","content":['
        '{"type":"text","text":"running it"},'
        '{"type":"tool_use","id":"x1","name":"Bash","input":{"command":"pytest -q","description":"run tests"}},'
        '{"type":"tool_use","id":"x2","name":"Read","input":{"file_path":"/proj/src/search.py"}}'
        ']}}',
        # user turn carrying tool_result blocks (one error)
        '{"type":"user","uuid":"u1","parentUuid":"a1","timestamp":"t",'
        '"message":{"role":"user","content":['
        '{"type":"tool_result","tool_use_id":"x1","is_error":true,"content":"boom"},'
        '{"type":"tool_result","tool_use_id":"x2","is_error":false,"content":"ok"}'
        ']}}',
        # another assistant turn: Edit (file_path) + Bash again (dedup commands)
        '{"type":"assistant","uuid":"a2","parentUuid":"u1","timestamp":"t",'
        '"message":{"role":"assistant","content":['
        '{"type":"tool_use","id":"x3","name":"Edit","input":{"file_path":"/proj/src/storage.py"}},'
        '{"type":"tool_use","id":"x4","name":"Bash","input":{"command":"pytest -q"}}'
        ']}}',
    ]
    p.write_text("\n".join(lines))

    result = parse_claude_code_jsonl(str(p))
    meta = result["code_meta"]

    assert meta["files"] == ["/proj/src/search.py", "/proj/src/storage.py"]
    assert meta["commands"] == ["pytest -q"]  # deduped
    assert meta["tools"] == ["Bash", "Edit", "Read"]  # sorted unique
    assert meta["error_count"] == 1


def test_parse_claude_code_jsonl_no_tools_empty_code_meta(tmp_path):
    """T20 (RED, AC2): a session with no tool blocks yields empty code_meta."""
    p = tmp_path / "plain.jsonl"
    lines = [
        '{"type":"user","uuid":"u1","parentUuid":null,"timestamp":"t",'
        '"message":{"role":"user","content":"just text"}}',
    ]
    p.write_text("\n".join(lines))

    meta = parse_claude_code_jsonl(str(p))["code_meta"]
    assert meta == {"files": [], "commands": [], "tools": [], "error_count": 0}


def test_parse_chat_json_basic(tmp_path):
    """T5b (RED): chat JSON with conversations -> list of session dicts.

    Spec: docs/architecture/chat-import-schema.md
    """
    p = tmp_path / "chats.json"
    data = {
        "schema_version": 1,
        "exported_at": "2026-05-26T00:00:00Z",
        "user": {"uuid": "u1"},
        "conversations": [
            {
                "uuid": "conv-1",
                "name": "MCP setup question",
                "summary": "Discussed how to configure MCP servers.",
                "created_at": "2026-05-01T00:00:00Z",
                "updated_at": "2026-05-01T01:00:00Z",
                "account": {"uuid": "u1"},
                "chat_messages": [
                    {
                        "uuid": "m1",
                        "sender": "human",
                        "text": "How do I configure MCP?",
                        "created_at": "2026-05-01T00:00:00Z",
                        "parent_message_uuid": "00000000-0000-4000-8000-000000000000",
                    },
                    {
                        "uuid": "m2",
                        "sender": "assistant",
                        "text": "Add the server to settings.",
                        "created_at": "2026-05-01T00:00:05Z",
                        "parent_message_uuid": "m1",
                    },
                ],
            }
        ],
    }
    p.write_text(json.dumps(data))

    sessions = parse_chat_json(str(p))

    assert len(sessions) == 1
    s = sessions[0]
    assert s["session_id"] == "conv-1"
    assert s["title"] == "MCP setup question"
    assert len(s["turns"]) == 2

    t0 = s["turns"][0]
    assert t0["turn_id"] == "m1"
    assert t0["role"] == "user"  # 'human' normalized -> 'user'
    assert t0["text"] == "How do I configure MCP?"
    assert t0["timestamp"] == "2026-05-01T00:00:00Z"
    assert t0["parent_id"] == "00000000-0000-4000-8000-000000000000"

    t1 = s["turns"][1]
    assert t1["role"] == "assistant"
    assert t1["parent_id"] == "m1"

    # conversation-level metadata preserved in extra
    assert s["extra"]["summary"] == "Discussed how to configure MCP servers."
    assert s["extra"]["created_at"] == "2026-05-01T00:00:00Z"
    assert s["extra"]["updated_at"] == "2026-05-01T01:00:00Z"


def test_parse_chat_json_empty_conversations(tmp_path):
    """T5b: empty conversations list -> empty list."""
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"schema_version": 1, "conversations": []}))
    assert parse_chat_json(str(p)) == []


def test_parse_chat_json_multiple_conversations(tmp_path):
    """T5b: multiple conversations -> one session dict per conversation, dedup keys preserved."""
    p = tmp_path / "multi.json"
    data = {
        "schema_version": 1,
        "conversations": [
            {
                "uuid": f"conv-{i}",
                "name": f"Session {i}",
                "summary": "",
                "created_at": "2026-05-01T00:00:00Z",
                "updated_at": "2026-05-01T00:00:00Z",
                "chat_messages": [
                    {
                        "uuid": f"m-{i}-1",
                        "sender": "human",
                        "text": f"msg from {i}",
                        "created_at": "2026-05-01T00:00:00Z",
                    }
                ],
            }
            for i in range(3)
        ],
    }
    p.write_text(json.dumps(data))

    sessions = parse_chat_json(str(p))
    assert [s["session_id"] for s in sessions] == ["conv-0", "conv-1", "conv-2"]
    assert all(len(s["turns"]) == 1 for s in sessions)


def test_stream_chat_sessions_yields_lazily(tmp_path):
    """T24 (RED): stream_chat_sessions returns an iterator (not a materialized
    list) yielding one session dict per conversation, equivalent to
    parse_chat_json. Streaming keeps peak memory to one conversation for the
    91MB real corpus (json.load would spike to ~600MB-1GB)."""
    p = tmp_path / "multi.json"
    data = {
        "schema_version": 1,
        "conversations": [
            {
                "uuid": f"conv-{i}",
                "name": f"Session {i}",
                "summary": "s",
                "created_at": "2026-05-01T00:00:00Z",
                "updated_at": "2026-05-01T00:00:00Z",
                "chat_messages": [
                    {"uuid": f"m-{i}", "sender": "human", "text": f"msg {i}",
                     "created_at": "2026-05-01T00:00:00Z", "parent_message_uuid": None},
                ],
            }
            for i in range(3)
        ],
    }
    p.write_text(json.dumps(data))

    stream = stream_chat_sessions(str(p))
    assert isinstance(stream, Iterator)

    sessions = list(stream)
    assert [s["session_id"] for s in sessions] == ["conv-0", "conv-1", "conv-2"]
    s0 = sessions[0]
    assert s0["title"] == "Session 0"
    assert s0["turns"][0]["role"] == "user"  # 'human' normalized
    assert s0["turns"][0]["text"] == "msg 0"
    assert s0["extra"]["summary"] == "s"


def test_stream_chat_sessions_warns_on_unknown_sender(tmp_path, caplog):
    """T25 (RED): an unrecognized chat sender (boundary validation of the
    user-curated JSON) is logged as a warning and kept as-is, not silently
    swallowed."""
    import logging

    p = tmp_path / "weird.json"
    data = {
        "schema_version": 1,
        "conversations": [
            {"uuid": "c1", "name": "n", "summary": "", "created_at": "t", "updated_at": "t",
             "chat_messages": [
                 {"uuid": "m1", "sender": "tool", "text": "hi", "created_at": "t",
                  "parent_message_uuid": None},
             ]},
        ],
    }
    p.write_text(json.dumps(data))

    with caplog.at_level(logging.WARNING, logger="mindpalace.parsing"):
        sessions = list(stream_chat_sessions(str(p)))

    assert sessions[0]["turns"][0]["role"] == "tool"  # kept as-is
    warnings = [r for r in caplog.records if r.name == "mindpalace.parsing"]
    assert any("tool" in r.getMessage() for r in warnings)


def test_stream_chat_sessions_rejects_unknown_schema_version(tmp_path):
    """T24 (RED): streaming path enforces the same schema_version contract."""
    p = tmp_path / "future.json"
    p.write_text(json.dumps({"schema_version": 999, "conversations": []}))
    with pytest.raises(ValueError, match="schema_version"):
        list(stream_chat_sessions(str(p)))


def test_parse_chat_json_rejects_unknown_schema_version(tmp_path):
    """T5b (review feedback): reject unsupported chat schema_version with a clear error.

    Contract: docs/architecture/chat-import-schema.md pins schema_version=1.
    Silent parsing of unknown versions would risk downstream data corruption.
    """
    p = tmp_path / "future.json"
    p.write_text(json.dumps({"schema_version": 999, "conversations": []}))
    with pytest.raises(ValueError, match="schema_version"):
        parse_chat_json(str(p))
