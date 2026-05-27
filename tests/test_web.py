"""Tests for the FastAPI web UI (AC7).

Uses a real embedding model + real DB (closured into the app via
``create_app``) and FastAPI's TestClient. The app binds nothing here;
network binding is the CLI ``serve`` command's responsibility.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mindpalace.embedding import embed_chunk
from mindpalace.storage import init_db, store_session
from mindpalace.web import create_app


@pytest.fixture(scope="module")
def warm_model() -> None:
    embed_chunk("warmup")


def _populated_db(tmp_path: Path) -> str:
    db = str(tmp_path / "web.db")
    init_db(db)
    store_session(
        db,
        {"session_id": "code-1", "title": "MCP setup walkthrough", "extra": {},
         "turns": [
             {"turn_id": "t1", "role": "user", "text": "How do I set up MCP servers in Claude Code?",
              "timestamp": "2026-05-26T10:00:00Z", "parent_id": None},
             {"turn_id": "t2", "role": "assistant", "text": "Use claude mcp add to register a stdio server.",
              "timestamp": "2026-05-26T10:00:05Z", "parent_id": "t1"},
         ]},
        source="code", embed_fn=embed_chunk,
    )
    store_session(
        db,
        {"session_id": "chat-1", "title": "Talking about MCP", "extra": {},
         "turns": [
             {"turn_id": "m1", "role": "user", "text": "What is MCP exactly?",
              "timestamp": "2026-05-26T09:00:00Z", "parent_id": None},
         ]},
        source="chat", embed_fn=embed_chunk,
    )
    return db


def test_index_renders_search_form(tmp_path: Path, warm_model: None) -> None:
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<form" in resp.text
    assert 'name="q"' in resp.text


def test_search_renders_results(tmp_path: Path, warm_model: None) -> None:
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": "How do I set up MCP servers?"})
    assert resp.status_code == 200
    assert "MCP" in resp.text
    # session title should render
    assert "MCP setup walkthrough" in resp.text or "Talking about MCP" in resp.text


def test_search_source_filter(tmp_path: Path, warm_model: None) -> None:
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": "MCP", "source": "code", "top_k": 10})
    assert resp.status_code == 200
    # chat-only session title must not appear under a code filter
    assert "Talking about MCP" not in resp.text


def test_search_empty_query_returns_form_or_message(tmp_path: Path, warm_model: None) -> None:
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": ""})
    assert resp.status_code == 200


def test_search_escapes_html_in_results(tmp_path: Path, warm_model: None) -> None:
    """XSS guard: stored/queried content must be HTML-escaped in the page."""
    db = str(tmp_path / "xss.db")
    init_db(db)
    store_session(
        db,
        {"session_id": "x", "title": "<script>alert(1)</script>", "extra": {},
         "turns": [{"turn_id": "t1", "role": "user", "text": "<img src=x onerror=alert(2)> MCP",
                    "timestamp": "2026-05-26T10:00:00Z", "parent_id": None}]},
        source="code", embed_fn=embed_chunk,
    )
    client = TestClient(create_app(db))
    resp = client.get("/search", params={"q": "MCP"})
    assert resp.status_code == 200
    # Raw tags must not appear unescaped.
    assert "<script>alert(1)</script>" not in resp.text
    assert "<img src=x onerror=alert(2)>" not in resp.text
    # Escaped form should be present.
    assert "&lt;script&gt;" in resp.text or "&lt;img" in resp.text
