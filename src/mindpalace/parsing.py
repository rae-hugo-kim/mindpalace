"""Parsers for Claude session formats (Code JSONL, Chat JSON)."""
import json
from pathlib import Path
from typing import Any

_TURN_TYPES = ("user", "assistant")
_SENDER_ROLE_MAP = {"human": "user", "user": "user", "assistant": "assistant"}
_SUPPORTED_CHAT_SCHEMA_VERSIONS = {1}


def _extract_text(content: Any) -> str:
    """Flatten a message.content field to plain text.

    Accepts a string (returned as-is) or a list of content blocks
    (text-typed block bodies joined by newline).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def parse_claude_code_jsonl(path: str) -> dict:
    """Parse a Claude Code session JSONL file.

    Returns a dict with:
      session_id: str  (file stem; always present)
      title: str | None  (from ai-title record if any)
      turns: list[dict]  (user/assistant only; other record types skipped)
        each turn: {turn_id, role, text, timestamp, parent_id}
      extra: dict  (cwd, git_branch from first observed turn)
    """
    p = Path(path)
    session_id = p.stem
    title: str | None = None
    turns: list[dict] = []
    extra: dict = {}

    with p.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = obj.get("type")
            if t == "ai-title":
                title = obj.get("aiTitle")
            elif t in _TURN_TYPES:
                msg = obj.get("message") or {}
                turns.append(
                    {
                        "turn_id": obj.get("uuid", ""),
                        "role": t,
                        "text": _extract_text(msg.get("content")),
                        "timestamp": obj.get("timestamp", ""),
                        "parent_id": obj.get("parentUuid"),
                    }
                )
                if not extra:
                    extra = {
                        "cwd": obj.get("cwd"),
                        "git_branch": obj.get("gitBranch"),
                    }

    return {
        "session_id": session_id,
        "title": title,
        "turns": turns,
        "extra": extra,
    }


def parse_chat_json(path: str) -> list[dict]:
    """Parse a user-curated Claude chat export JSON.

    Input contract: docs/architecture/chat-import-schema.md (schema_version 1).

    Returns a list of session dicts (one per conversation). Each session:
      session_id: str  (conversation.uuid)
      title: str | None  (conversation.name)
      turns: list[dict]  (one per chat_messages entry)
        each turn: {turn_id, role, text, timestamp, parent_id}
      extra: dict  (summary, created_at, updated_at from conversation)
    """
    with Path(path).open() as f:
        data = json.load(f)

    sv = data.get("schema_version")
    if sv not in _SUPPORTED_CHAT_SCHEMA_VERSIONS:
        raise ValueError(
            f"unsupported chat schema_version: {sv!r} "
            f"(expected one of {sorted(_SUPPORTED_CHAT_SCHEMA_VERSIONS)})"
        )

    sessions: list[dict] = []
    for conv in data.get("conversations", []):
        turns: list[dict] = []
        for msg in conv.get("chat_messages", []):
            sender = msg.get("sender", "")
            turns.append(
                {
                    "turn_id": msg.get("uuid", ""),
                    "role": _SENDER_ROLE_MAP.get(sender, sender),
                    "text": msg.get("text", ""),
                    "timestamp": msg.get("created_at", ""),
                    "parent_id": msg.get("parent_message_uuid"),
                }
            )
        sessions.append(
            {
                "session_id": conv.get("uuid", ""),
                "title": conv.get("name"),
                "turns": turns,
                "extra": {
                    "summary": conv.get("summary", ""),
                    "created_at": conv.get("created_at", ""),
                    "updated_at": conv.get("updated_at", ""),
                },
            }
        )
    return sessions
