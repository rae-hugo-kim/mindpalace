"""Tests for mindpalace.parsing."""
from mindpalace.parsing import parse_claude_code_jsonl


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
