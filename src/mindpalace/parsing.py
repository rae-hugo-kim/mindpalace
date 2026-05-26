"""Parsers for Claude session formats (Code JSONL, Chat JSON)."""
import json
from pathlib import Path
from typing import Any

_TURN_TYPES = ("user", "assistant")


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
