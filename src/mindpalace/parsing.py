"""Parsers for Claude session formats (Code JSONL, Chat JSON)."""
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import ijson

from mindpalace.obs import get_logger

_log = get_logger("mindpalace.parsing")

_TURN_TYPES = ("user", "assistant")
_SENDER_ROLE_MAP = {"human": "user", "user": "user", "assistant": "assistant"}
_SUPPORTED_CHAT_SCHEMA_VERSIONS = {1}

# tool_use input keys that name a file on disk (AC2 code metadata).
_FILE_PATH_KEYS = ("file_path", "notebook_path")


def _scan_code_meta(content: Any, acc: dict) -> None:
    """Accumulate AC2 code metadata from a message.content block list.

    Walks tool_use blocks (tool name, file_path, Bash command) and
    tool_result blocks (is_error) and folds them into ``acc`` (sets for
    files/commands/tools, an int counter for errors). Non-list content
    (plain user text) carries no tool blocks and is ignored.
    """
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "tool_use":
            name = block.get("name")
            if name:
                acc["tools"].add(name)
            inp = block.get("input") or {}
            if isinstance(inp, dict):
                for key in _FILE_PATH_KEYS:
                    val = inp.get(key)
                    if isinstance(val, str) and val:
                        acc["files"].add(val)
                if name == "Bash":
                    cmd = inp.get("command")
                    if isinstance(cmd, str) and cmd:
                        acc["commands"].add(cmd)
        elif btype == "tool_result":
            if block.get("is_error"):
                acc["error_count"] += 1


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
      code_meta: dict  (AC2 derived index aggregated over the session:
        files, commands, tools — sorted unique lists — and error_count)
    """
    p = Path(path)
    session_id = p.stem
    title: str | None = None
    turns: list[dict] = []
    extra: dict = {}
    meta_acc = {"files": set(), "commands": set(), "tools": set(), "error_count": 0}

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
                _scan_code_meta(msg.get("content"), meta_acc)
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
        "code_meta": {
            "files": sorted(meta_acc["files"]),
            "commands": sorted(meta_acc["commands"]),
            "tools": sorted(meta_acc["tools"]),
            "error_count": meta_acc["error_count"],
        },
    }


def _conv_to_session(conv: dict) -> dict:
    """Transform one curated-export conversation into a session dict."""
    turns: list[dict] = []
    for msg in conv.get("chat_messages", []):
        sender = msg.get("sender", "")
        if sender not in _SENDER_ROLE_MAP:
            _log.warning(
                "unknown chat sender role %r in message %s (conversation %s); kept as-is",
                sender, msg.get("uuid", ""), conv.get("uuid", ""),
            )
        turns.append(
            {
                "turn_id": msg.get("uuid", ""),
                "role": _SENDER_ROLE_MAP.get(sender, sender),
                "text": msg.get("text", ""),
                "timestamp": msg.get("created_at", ""),
                "parent_id": msg.get("parent_message_uuid"),
            }
        )
    return {
        "session_id": conv.get("uuid", ""),
        "title": conv.get("name"),
        "turns": turns,
        "extra": {
            "summary": conv.get("summary", ""),
            "created_at": conv.get("created_at", ""),
            "updated_at": conv.get("updated_at", ""),
        },
    }


def _read_chat_schema_version(path: str) -> Any:
    """Stream just the top-level ``schema_version`` scalar (no full load)."""
    with Path(path).open("rb") as f:
        try:
            return next(ijson.items(f, "schema_version"))
        except StopIteration:
            return None


def stream_chat_sessions(path: str) -> Iterator[dict]:
    """Yield one session dict per conversation, streaming with ijson.

    Input contract: docs/architecture/chat-import-schema.md (schema_version 1).

    Unlike a ``json.load`` of the whole file (which spikes to ~600MB-1GB
    on the real 91MB corpus), this materializes only one conversation at
    a time, so peak memory stays bounded for end-to-end streaming import.

    Each yielded session:
      session_id: str  (conversation.uuid)
      title: str | None  (conversation.name)
      turns: list[dict]  (one per chat_messages entry:
        {turn_id, role, text, timestamp, parent_id})
      extra: dict  (summary, created_at, updated_at from conversation)

    Raises ValueError if schema_version is unsupported (checked before
    any conversation is yielded).
    """
    sv = _read_chat_schema_version(path)
    if sv not in _SUPPORTED_CHAT_SCHEMA_VERSIONS:
        raise ValueError(
            f"unsupported chat schema_version: {sv!r} "
            f"(expected one of {sorted(_SUPPORTED_CHAT_SCHEMA_VERSIONS)})"
        )

    with Path(path).open("rb") as f:
        for conv in ijson.items(f, "conversations.item"):
            yield _conv_to_session(conv)


def parse_chat_json(path: str) -> list[dict]:
    """Eager wrapper over :func:`stream_chat_sessions` returning a list.

    Kept for callers/tests that need random access; the streaming
    generator is preferred for large imports.
    """
    return list(stream_chat_sessions(path))
