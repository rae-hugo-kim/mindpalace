"""Chunking strategy: 1 turn = 1 chunk (v0 walking skeleton)."""


def chunk_session(session: dict, source: str) -> list[dict]:
    """Convert a parsed session dict into a flat list of chunk dicts.

    v0 policy: each turn becomes exactly one chunk. The chunker is source-agnostic;
    callers tag the chunks with ``source`` ("claude-code" or "claude-chat").

    Each returned chunk carries:
      chunk_id: str  (f"{session_id}:{turn_id}")
      session_id, turn_id: str
      source: str  (echoed from arg)
      title: str | None  (session.title)
      role: str  (turn.role)
      text: str  (turn.text)
      timestamp: str  (turn.timestamp)
      parent_id: str | None  (turn.parent_id)
      extra: dict  (session.extra, shared across chunks of the same session)
    """
    chunks: list[dict] = []
    session_id = session.get("session_id", "")
    title = session.get("title")
    extra = session.get("extra", {})
    for turn in session.get("turns", []):
        text = turn.get("text", "")
        if not text.strip():
            continue
        turn_id = turn.get("turn_id", "")
        chunks.append(
            {
                "chunk_id": f"{session_id}:{turn_id}",
                "session_id": session_id,
                "turn_id": turn_id,
                "source": source,
                "title": title,
                "role": turn.get("role", ""),
                "text": turn.get("text", ""),
                "timestamp": turn.get("timestamp", ""),
                "parent_id": turn.get("parent_id"),
                "extra": extra,
            }
        )
    return chunks
