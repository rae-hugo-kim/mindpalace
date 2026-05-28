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


def _db_with_code_meta(tmp_path: Path) -> str:
    db = str(tmp_path / "meta-web.db")
    init_db(db)
    store_session(
        db,
        {"session_id": "code-search", "title": "Edited the ranker", "extra": {},
         "turns": [{"turn_id": "t1", "role": "user", "text": "refactor the ranking logic",
                    "timestamp": "2026-05-20T10:00:00Z", "parent_id": None}],
         "code_meta": {"files": ["/proj/src/search.py"], "commands": ["pytest -q"],
                       "tools": ["Edit", "Bash"], "error_count": 1}},
        source="code", embed_fn=embed_chunk,
    )
    store_session(
        db,
        {"session_id": "code-storage", "title": "Edited storage", "extra": {},
         "turns": [{"turn_id": "t1", "role": "user", "text": "refactor the ranking logic",
                    "timestamp": "2026-01-05T10:00:00Z", "parent_id": None}],
         "code_meta": {"files": ["/proj/src/storage.py"], "commands": [],
                       "tools": ["Edit"], "error_count": 0}},
        source="code", embed_fn=embed_chunk,
    )
    return db


def test_search_form_has_meta_filter_inputs(tmp_path: Path, warm_model: None) -> None:
    """T22 (RED): the search form exposes file/time/title filter inputs."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/")
    assert resp.status_code == 200
    for name in ("file_like", "since", "until", "title_like"):
        assert f'name="{name}"' in resp.text, name


def test_search_file_like_filter_in_web(tmp_path: Path, warm_model: None) -> None:
    """T22 (RED): file_like query param restricts to sessions touching that file."""
    client = TestClient(create_app(_db_with_code_meta(tmp_path)))
    resp = client.get("/search", params={"q": "refactor the ranking", "top_k": 10,
                                          "file_like": "search.py"})
    assert resp.status_code == 200
    assert "Edited the ranker" in resp.text
    assert "Edited storage" not in resp.text


def test_search_time_filter_in_web(tmp_path: Path, warm_model: None) -> None:
    """T22 (RED): since/until bound results by timestamp."""
    client = TestClient(create_app(_db_with_code_meta(tmp_path)))
    resp = client.get("/search", params={"q": "refactor the ranking", "top_k": 10,
                                          "since": "2026-05-01", "until": "2026-06-01"})
    assert resp.status_code == 200
    # Only the May session (code-search) is in window; January one excluded.
    assert "Edited the ranker" in resp.text
    assert "Edited storage" not in resp.text


def test_search_displays_latency(tmp_path: Path, warm_model: None) -> None:
    """T22 (RED, AC15 surfacing): results page shows query latency in ms."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": "How do I set up MCP servers?"})
    assert resp.status_code == 200
    assert "ms" in resp.text
    assert "latency" in resp.text.lower()


def test_search_shows_code_meta_badge(tmp_path: Path, warm_model: None) -> None:
    """T22 (RED): code hits show a metadata badge (files/tools/errors)."""
    client = TestClient(create_app(_db_with_code_meta(tmp_path)))
    resp = client.get("/search", params={"q": "refactor the ranking", "top_k": 10,
                                          "file_like": "search.py"})
    assert resp.status_code == 200
    # badge reflects code_meta: 1 file, 2 tools, 1 error for code-search
    assert "search.py" in resp.text
    assert "errors=1" in resp.text or "1 error" in resp.text


def test_search_context_shows_neighbor_turns(tmp_path: Path, warm_model: None) -> None:
    """T23 (RED): context=N renders ±N surrounding turns under the hit with a
    ► marker on the hit row (web equivalent of CLI --context)."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": "How do I set up MCP servers?",
                                          "top_k": 1, "context": 1})
    assert resp.status_code == 200
    assert "►" in resp.text
    # The neighbor turn t2 text should appear via context expansion.
    assert "claude mcp add" in resp.text


def test_search_form_has_context_input(tmp_path: Path, warm_model: None) -> None:
    """T23 (RED): the form exposes a context (±N) control."""
    resp = TestClient(create_app(_populated_db(tmp_path))).get("/")
    assert 'name="context"' in resp.text


def test_neighbors_route_lists_opposite_source(tmp_path: Path, warm_model: None) -> None:
    """T23 (RED): GET /neighbors?session_id=code-1 lists the chat session
    imported the same day (AC6 weak learn↔work link, surfaced in the web)."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/neighbors", params={"session_id": "code-1", "days": 3})
    assert resp.status_code == 200
    # code-1 (code) ↔ chat-1 (chat) on 2026-05-26 are within ±3 days.
    assert "Talking about MCP" in resp.text


def test_neighbors_route_unknown_session_friendly(tmp_path: Path, warm_model: None) -> None:
    """T23 (RED): unknown session id → friendly empty message, still 200."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/neighbors", params={"session_id": "no-such"})
    assert resp.status_code == 200
    assert "neighbor" in resp.text.lower()


def test_hit_links_to_neighbors(tmp_path: Path, warm_model: None) -> None:
    """T23 (RED): each hit offers a link to its session's neighbors."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": "How do I set up MCP servers?", "top_k": 1})
    assert resp.status_code == 200
    assert "/neighbors?session_id=" in resp.text


def test_form_default_context_is_nonzero(tmp_path: Path, warm_model: None) -> None:
    """T27 (RED): the form ships with context pre-set so hits show surrounding
    turns out of the box (a lone short turn is meaningless on its own)."""
    resp = TestClient(create_app(_populated_db(tmp_path))).get("/")
    assert 'name="context" value="2"' in resp.text


def test_search_default_shows_context(tmp_path: Path, warm_model: None) -> None:
    """T27 (RED): a search with no explicit context still renders context rows."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": "How do I set up MCP servers?", "top_k": 1})
    assert resp.status_code == 200
    assert 'class="ctx"' in resp.text


def test_session_route_renders_full_session(tmp_path: Path, warm_model: None) -> None:
    """T27 (RED): /session?session_id=… shows the whole session's turns in order
    (the seed's third display level: chunk → ±N → full session context)."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/session", params={"session_id": "code-1"})
    assert resp.status_code == 200
    assert "How do I set up MCP servers in Claude Code?" in resp.text
    assert "Use claude mcp add to register a stdio server." in resp.text
    assert 'href="/"' in resp.text  # back-to-search link


def test_session_route_highlights_hit_turn(tmp_path: Path, warm_model: None) -> None:
    """T27 (RED): hl=<turn_id> marks the matched turn so the user lands on it."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/session", params={"session_id": "code-1", "hl": "t2"})
    assert resp.status_code == 200
    assert "►" in resp.text


def test_session_route_unknown_friendly(tmp_path: Path, warm_model: None) -> None:
    """T27 (RED): unknown session id → friendly message, still 200."""
    resp = TestClient(create_app(_populated_db(tmp_path))).get(
        "/session", params={"session_id": "no-such"}
    )
    assert resp.status_code == 200
    assert "찾을 수 없" in resp.text  # friendly not-found
    assert 'href="/"' in resp.text   # back-to-search link still offered


def test_hit_links_to_session(tmp_path: Path, warm_model: None) -> None:
    """T27 (RED): each hit links to its full-session view, carrying the hit turn."""
    client = TestClient(create_app(_populated_db(tmp_path)))
    resp = client.get("/search", params={"q": "How do I set up MCP servers?", "top_k": 1})
    assert resp.status_code == 200
    assert "/session?session_id=" in resp.text


def test_form_number_inputs_have_visible_labels(tmp_path: Path, warm_model: None) -> None:
    """T28 (RED): the bare number inputs (top_k, context) carry visible text
    labels so the user knows what 5 and 2 mean without hovering."""
    resp = TestClient(create_app(_populated_db(tmp_path))).get("/")
    assert resp.status_code == 200
    assert "<label" in resp.text
    assert "결과" in resp.text   # top_k label
    assert "맥락" in resp.text   # context label


def test_web_hybrid_keyword_section(tmp_path: Path, warm_model: None) -> None:
    """T29 (RED): an exact rare term shows a keyword-match section in the web
    UI even though the embedding can't rank it."""
    db = str(tmp_path / "hyb-web.db")
    init_db(db)
    store_session(db, {
        "session_id": "drug", "title": "마운자로 부작용", "extra": {},
        "turns": [{"turn_id": "t1", "role": "user",
                   "text": "마운자로 5mg 부작용 설사 정상인가요",
                   "timestamp": "2026-05-10T00:00:00Z", "parent_id": None}],
    }, source="chat", embed_fn=embed_chunk)
    store_session(db, {
        "session_id": "mcp", "title": "MCP", "extra": {},
        "turns": [{"turn_id": "t1", "role": "user",
                   "text": "configure MCP servers", "timestamp": "2026-05-11T00:00:00Z",
                   "parent_id": None}],
    }, source="code", embed_fn=embed_chunk)

    resp = TestClient(create_app(db)).get("/search", params={"q": "마운자로", "top_k": 3})
    assert resp.status_code == 200
    assert "마운자로 5mg 부작용" in resp.text
    assert "keyword" in resp.text.lower() or "정확" in resp.text


def test_web_text_preserves_whitespace(tmp_path: Path, warm_model: None) -> None:
    """T30 (RED): result text is rendered with pre-wrap so newlines / markdown
    layout survive instead of collapsing into one run-on line."""
    resp = TestClient(create_app(_populated_db(tmp_path))).get("/")
    assert "pre-wrap" in resp.text


def test_web_long_context_turn_is_collapsible(tmp_path: Path, warm_model: None) -> None:
    """T30/T31 (RED): a long assistant turn shown as *context* (not the hit)
    folds into a collapsible <details> so it doesn't flood the page; the full
    text stays in the DOM. (The hit turn itself is never folded — see
    test_web_hit_turn_not_folded.)"""
    db = str(tmp_path / "long.db")
    init_db(db)
    long_text = "사고 과정입니다. " + ("이것은 매우 긴 추론 텍스트입니다. " * 40)
    store_session(db, {
        "session_id": "s", "title": "긴 추론", "extra": {},
        "turns": [
            {"turn_id": "t1", "role": "user", "text": "ZQMARKER 짧은 질문",
             "timestamp": "2026-05-10T00:00:00Z", "parent_id": None},
            {"turn_id": "t2", "role": "assistant", "text": long_text,
             "timestamp": "2026-05-10T00:00:05Z", "parent_id": "t1"},
        ],
    }, source="chat", embed_fn=embed_chunk)

    # keyword hit is the short user turn t1; t2 (long assistant) appears as context
    resp = TestClient(create_app(db)).get(
        "/search", params={"q": "ZQMARKER", "top_k": 1, "context": 1}
    )
    assert resp.status_code == 200
    assert "<details" in resp.text          # the long context turn folds
    assert "매우 긴 추론" in resp.text        # full text still in DOM


def test_web_roles_visually_distinguished(tmp_path: Path, warm_model: None) -> None:
    """T30 (RED): turns carry a role class so user vs assistant can be told
    apart at a glance."""
    resp = TestClient(create_app(_populated_db(tmp_path))).get(
        "/search", params={"q": "How do I set up MCP servers?", "top_k": 1}
    )
    assert "role-user" in resp.text or "role-assistant" in resp.text


def test_web_long_hit_renders_snippet_plus_collapsed_body(tmp_path: Path, warm_model: None) -> None:
    """T32 (RED): long matched turns become a scannable card — a snippet that
    shows the reason (matched phrase) + a collapsed body the user can expand.
    Replaces T31's 'hit never folds' rule: the snippet preserves visibility of
    the matched/answer-bearing phrase without flooding the page."""
    db = str(tmp_path / "longhit.db")
    init_db(db)
    long_ans = ("앞쪽 추론 문장이 한참 이어집니다. " * 20
                + "ANSWERMARK 결론은 이렇습니다. "
                + "추가 설명이 또 한참 이어집니다. " * 20)
    store_session(db, {
        "session_id": "s", "title": "긴 답변", "extra": {},
        "turns": [{"turn_id": "t1", "role": "assistant", "text": long_ans,
                   "timestamp": "2026-05-10T00:00:00Z", "parent_id": None}],
    }, source="chat", embed_fn=embed_chunk)

    resp = TestClient(create_app(db)).get(
        "/search", params={"q": "ANSWERMARK", "top_k": 1, "context": 0}
    )
    assert resp.status_code == 200
    assert 'class="hit-body"' in resp.text   # collapsed full body
    assert "<mark>" in resp.text              # keyword highlighted in snippet
    assert "ANSWERMARK" in resp.text          # matched phrase visible (snippet)


def test_web_keyword_snippet_highlights_match(tmp_path: Path, warm_model: None) -> None:
    """T32 (RED): a keyword hit's snippet wraps the matched substring in
    <mark> so the reason for the hit is obvious at a glance."""
    db = str(tmp_path / "mark.db")
    init_db(db)
    text = ("앞쪽 문맥 한참. " * 30) + " UNIQTOKEN 결론. " + ("뒤쪽 문맥 한참. " * 30)
    store_session(db, {
        "session_id": "u", "title": "highlight test", "extra": {},
        "turns": [{"turn_id": "t1", "role": "assistant", "text": text,
                   "timestamp": "2026-05-10T00:00:00Z", "parent_id": None}],
    }, source="chat", embed_fn=embed_chunk)

    resp = TestClient(create_app(db)).get(
        "/search", params={"q": "UNIQTOKEN", "top_k": 1, "context": 0}
    )
    assert "<mark>UNIQTOKEN</mark>" in resp.text


def test_web_short_hit_not_folded(tmp_path: Path, warm_model: None) -> None:
    """T32 (RED): short hits stay fully inline (no body fold) — folding
    short turns adds clicks without a readability benefit."""
    resp = TestClient(create_app(_populated_db(tmp_path))).get(
        "/search", params={"q": "How do I set up MCP servers?", "top_k": 1, "context": 0}
    )
    assert resp.status_code == 200
    assert 'class="hit-body"' not in resp.text  # short hit: no body fold


def test_web_semantic_section_collapsed_when_keyword_hits(tmp_path: Path, warm_model: None) -> None:
    """T31 (RED): when exact keyword matches exist, the noisier semantic
    results are demoted into a collapsed section."""
    db = str(tmp_path / "demote.db")
    init_db(db)
    store_session(db, {
        "session_id": "drug", "title": "마운자로", "extra": {},
        "turns": [{"turn_id": "t1", "role": "user", "text": "마운자로 부작용 설사",
                   "timestamp": "2026-05-10T00:00:00Z", "parent_id": None}],
    }, source="chat", embed_fn=embed_chunk)
    store_session(db, {
        "session_id": "noise", "title": "잡담", "extra": {},
        "turns": [{"turn_id": "t1", "role": "user", "text": "청사초롱 노래 가사",
                   "timestamp": "2026-05-11T00:00:00Z", "parent_id": None}],
    }, source="chat", embed_fn=embed_chunk)

    resp = TestClient(create_app(db)).get("/search", params={"q": "마운자로", "top_k": 3})
    assert resp.status_code == 200
    assert "semantic-section" in resp.text  # semantic demoted into a collapsed block


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
