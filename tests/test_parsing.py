"""Tests for mindpalace.parsing."""
import json

import pytest

from mindpalace.parsing import parse_chat_json, parse_claude_code_jsonl


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


def test_parse_chat_json_rejects_unknown_schema_version(tmp_path):
    """T5b (review feedback): reject unsupported chat schema_version with a clear error.

    Contract: docs/architecture/chat-import-schema.md pins schema_version=1.
    Silent parsing of unknown versions would risk downstream data corruption.
    """
    p = tmp_path / "future.json"
    p.write_text(json.dumps({"schema_version": 999, "conversations": []}))
    with pytest.raises(ValueError, match="schema_version"):
        parse_chat_json(str(p))
