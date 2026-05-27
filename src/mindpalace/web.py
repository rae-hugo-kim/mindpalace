"""FastAPI web UI for the vault (seed AC7).

A single-user, server-rendered search page. The DB path is closured
into the app via ``create_app(db_path)`` so the same module can be
driven by tests (TestClient) and by the CLI ``serve`` command (which
binds 0.0.0.0 for Tailscale/VPN mesh access from other devices).

All user- and corpus-derived strings are passed through ``html.escape``
before interpolation — the corpus contains arbitrary chat/code text,
including HTML and scripts, so escaping is a hard requirement.
"""
from __future__ import annotations

import html
import time

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from mindpalace.embedding import embed_chunk
from mindpalace.search import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    find_neighbors,
    get_chunk_context,
    get_code_meta,
    get_session_turns,
    hybrid_search,
)

_DEFAULT_CONTEXT = 2

_PAGE_HEAD = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mindpalace</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;line-height:1.5}
 form{display:flex;gap:.5rem;flex-wrap:wrap;align-items:end;margin-bottom:1.5rem}
 input[type=text]{flex:1;min-width:14rem;padding:.5rem;font-size:1rem}
 select,input[type=number]{padding:.5rem}
 label{display:flex;flex-direction:column;font-size:.7rem;color:#666;gap:.15rem}
 label input[type=number]{width:4.5rem}
 button{padding:.5rem 1rem;font-size:1rem;cursor:pointer}
 .hit{border:1px solid #ddd;border-radius:8px;padding:.75rem 1rem;margin:.75rem 0}
 .hit.low{border-color:#e0b000;background:#fffdf3}
 .meta{color:#666;font-size:.85rem;margin-bottom:.35rem}
 .badge{color:#555;background:#f3f4f6;border-radius:6px;padding:.3rem .5rem;margin-top:.4rem;font-size:.8rem;font-family:ui-monospace,monospace}
 .warn{color:#b35900;font-weight:600}
 .empty{color:#666}
 .latency{color:#888;font-size:.8rem}
 .ctx{border-left:2px solid #eee;margin:.5rem 0 0 .5rem;padding-left:.6rem;font-size:.9rem}
 .ctx .row{color:#777;margin:.15rem 0}
 .ctx .row.hit{color:#111;font-weight:600;background:none;border:none;padding:0}
 .nlink{font-size:.8rem;margin-top:.35rem}
 .turntext{white-space:pre-wrap;word-break:break-word}
 details.turn>summary{cursor:pointer;color:#666;list-style:none}
 details.turn>summary::-webkit-details-marker{display:none}
 details.turn>summary::before{content:"▸ ";color:#999}
 details.turn[open]>summary::before{content:"▾ "}
 details.turn>summary .pv{color:#888}
 .role-user{border-left:3px solid #2b6cb0;padding-left:.5rem}
 .role-assistant{border-left:3px solid #e2e8f0;padding-left:.5rem;color:#333}
 details.semantic-section>summary{cursor:pointer;color:#888;font-size:.95rem;margin:1rem 0 .5rem;font-weight:600}
</style></head><body>
<h1>mindpalace</h1>
"""

_PAGE_TAIL = "</body></html>"


def _form(
    q: str = "",
    source: str = "",
    top_k: int = 5,
    file_like: str = "",
    since: str = "",
    until: str = "",
    title_like: str = "",
    context: int = _DEFAULT_CONTEXT,
) -> str:
    qs = html.escape(q)
    code_sel = " selected" if source == "code" else ""
    chat_sel = " selected" if source == "chat" else ""
    fl = html.escape(file_like)
    sn = html.escape(since)
    un = html.escape(until)
    tl = html.escape(title_like)
    return f"""<form action="/search" method="get">
 <input type="text" name="q" value="{qs}" placeholder="자연어로 검색…" autofocus>
 <label>소스<select name="source">
  <option value="">all sources</option>
  <option value="code"{code_sel}>code</option>
  <option value="chat"{chat_sel}>chat</option>
 </select></label>
 <label>결과 수<input type="number" name="top_k" value="{int(top_k)}" min="1" max="50" title="검색 결과 개수 (top_k)"></label>
 <label>맥락 ±<input type="number" name="context" value="{int(context)}" min="0" max="10" title="hit 앞뒤로 함께 보여줄 turn 수"></label>
 <input type="text" name="file_like" value="{fl}" placeholder="file path…" title="code file path substring">
 <input type="text" name="since" value="{sn}" placeholder="since (YYYY-MM-DD)" title="since">
 <input type="text" name="until" value="{un}" placeholder="until (YYYY-MM-DD)" title="until">
 <input type="text" name="title_like" value="{tl}" placeholder="title…" title="session title substring">
 <button type="submit">search</button>
</form>"""


_COLLAPSE_CHARS = 280


def _turn_text(text: str, role: str = "", foldable: bool = True) -> str:
    """Render turn text with preserved whitespace; optionally fold long turns.

    A role class lets user vs assistant be told apart at a glance. When
    ``foldable`` and the text is long, it collapses into a no-JS <details>
    preview (full text stays in the DOM). The matched (hit) turn and user
    turns pass ``foldable=False`` so the answer is never hidden — chat
    exports bundle an assistant's reasoning and answer into one turn, so
    folding the hit would hide the answer too.
    """
    raw = text or ""
    role_cls = f"role-{role}" if role in ("user", "assistant") else ""
    escaped = html.escape(raw)
    if not foldable or len(raw) <= _COLLAPSE_CHARS:
        return f'<div class="turntext {role_cls}">{escaped}</div>'
    preview = html.escape(raw[:120].replace("\n", " "))
    return (
        f'<details class="turn {role_cls}"><summary>'
        f'<span class="pv">{preview}…</span></summary>'
        f'<div class="turntext">{escaped}</div></details>'
    )


def _code_meta_badge(meta: dict | None) -> str:
    """Render a compact code-metadata badge (AC2) for a code hit."""
    if not meta:
        return ""
    files = meta.get("files") or []
    tools = meta.get("tools") or []
    errors = int(meta.get("error_count") or 0)
    file_str = html.escape(", ".join(files[:3])) + ("…" if len(files) > 3 else "")
    tool_str = html.escape(", ".join(tools))
    return (
        '<div class="badge">'
        f"files={len(files)} · tools={len(tools)} · errors={errors}"
        + (f"<br>↳ {file_str}" if files else "")
        + (f"<br>tools: {tool_str}" if tools else "")
        + "</div>"
    )


def _render_context(rows: list[dict]) -> str:
    """Render ±N surrounding turns; the hit row is marked with ►."""
    if not rows:
        return ""
    parts = ['<div class="ctx">']
    for r in rows:
        is_hit = r.get("is_hit")
        marker = "► " if is_hit else "  "
        role = html.escape(r.get("role") or "")
        cls = "row hit" if is_hit else "row"
        foldable = (r.get("role") == "assistant") and not is_hit
        body = _turn_text(r.get("text") or "", r.get("role") or "", foldable=foldable)
        parts.append(f'<div class="{cls}">{marker}{role}: {body}</div>')
    parts.append("</div>")
    return "".join(parts)


def _render_hit(
    i: int,
    hit: dict,
    code_meta: dict | None = None,
    context_rows: list[dict] | None = None,
) -> str:
    title = html.escape(str(hit.get("title") or ""))
    role = html.escape(hit.get("role") or "")
    source = html.escape(hit.get("source") or "")
    session_id = hit.get("session_id") or ""
    chunk_id = hit.get("chunk_id") or ""
    turn_id = chunk_id[len(session_id) + 1:] if chunk_id.startswith(session_id + ":") else ""
    sid_q = html.escape(session_id)
    low = hit.get("low_confidence")
    cls = "hit low" if low else "hit"
    warn = ' <span class="warn">⚠ low-confidence</span>' if low else ""
    distance = hit.get("distance")
    score = "exact match" if distance is None else f"distance={distance:.4f}"
    nlink = (
        '<div class="nlink">'
        f'<a href="/session?session_id={sid_q}&hl={html.escape(turn_id)}">📄 전체 세션</a>'
        f' · <a href="/neighbors?session_id={sid_q}">↔ neighbors (학습↔작업)</a>'
        "</div>"
    )
    return (
        f'<div class="{cls}">'
        f'<div class="meta">[{i}] {score} · '
        f"source={source} · role={role} · title={title}{warn}</div>"
        f"{_turn_text(hit.get('text') or '', hit.get('role') or '', foldable=False)}"
        f"{_code_meta_badge(code_meta)}"
        f"{_render_context(context_rows or [])}"
        f"{nlink}"
        f"</div>"
    )


def create_app(db_path: str) -> FastAPI:
    app = FastAPI(title="mindpalace", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _PAGE_HEAD + _form() + _PAGE_TAIL

    @app.get("/search", response_class=HTMLResponse)
    def search_page(
        q: str = Query("", description="natural-language query"),
        source: str = Query("", description="code|chat|empty"),
        top_k: int = Query(5, ge=1, le=50),
        min_confidence: float = Query(DEFAULT_CONFIDENCE_THRESHOLD),
        file_like: str = Query("", description="code file path substring"),
        since: str = Query("", description="ISO lower bound on timestamp"),
        until: str = Query("", description="ISO upper bound on timestamp"),
        title_like: str = Query("", description="session title substring"),
        context: int = Query(_DEFAULT_CONTEXT, ge=0, le=10, description="±N surrounding turns"),
    ) -> str:
        body = _form(
            q=q, source=source, top_k=top_k,
            file_like=file_like, since=since, until=until, title_like=title_like,
            context=context,
        )

        if not q.strip():
            body += '<p class="empty">쿼리를 입력하세요.</p>'
            return _PAGE_HEAD + body + _PAGE_TAIL

        t0 = time.perf_counter()
        out = hybrid_search(
            db_path,
            q,
            embed_chunk,
            top_k=top_k,
            confidence_threshold=min_confidence,
            where_source=source or None,
            where_since=since or None,
            where_until=until or None,
            where_title_like=title_like or None,
            where_file_like=file_like or None,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        keyword, semantic = out["keyword"], out["semantic"]
        total = len(keyword) + len(semantic)

        body += (
            f'<p class="latency">latency {latency_ms:.0f}ms · {total} hits '
            f"(keyword {len(keyword)} · semantic {len(semantic)})</p>"
        )

        meta_cache: dict[str, dict | None] = {}

        def _render_list(hits: list[dict]) -> str:
            parts = []
            for i, h in enumerate(hits, start=1):
                cm = None
                sid = h["session_id"]
                if h.get("source") == "code":
                    if sid not in meta_cache:
                        meta_cache[sid] = get_code_meta(db_path, sid)
                    cm = meta_cache[sid]
                ctx_rows = None
                if context > 0:
                    turn_id = h["chunk_id"][len(sid) + 1:]
                    ctx_rows = get_chunk_context(db_path, sid, turn_id, window=context)
                parts.append(_render_hit(i, h, code_meta=cm, context_rows=ctx_rows))
            return "".join(parts)

        if total == 0:
            active = [
                name for name, val in (
                    ("source", source), ("file_like", file_like), ("since", since),
                    ("until", until), ("title_like", title_like),
                ) if val
            ]
            hint = (
                f" 활성 필터({', '.join(active)})를 해제하거나" if active
                else " 소스 필터를 해제하거나"
            )
            body += f'<p class="empty">결과 없음 (0 hits) —{hint} 쿼리를 넓혀 보세요.</p>'
            return _PAGE_HEAD + body + _PAGE_TAIL

        if keyword:
            body += f'<h3>🔑 정확히 일치 (keyword) — {len(keyword)}</h3>'
            body += _render_list(keyword)

        if semantic:
            if keyword:
                # Exact matches already answered the query; embeddings can't
                # rank rare proper nouns, so demote the noisier semantic
                # results into a collapsed section the user can opt into.
                body += (
                    '<details class="semantic-section"><summary>'
                    f"🧭 semantic — {len(semantic)}건 (정확도 낮을 수 있음, 펼쳐 보기)"
                    "</summary>"
                )
                body += _render_list(semantic)
                body += "</details>"
            else:
                if all(r["low_confidence"] for r in semantic):
                    body += (
                        f'<p class="warn">🧭 semantic — high-confidence 매치 없음, 아래 '
                        f"{len(semantic)}건은 best-effort(모두 low-confidence)입니다.</p>"
                    )
                else:
                    body += f"<h3>🧭 semantic — {len(semantic)}</h3>"
                body += _render_list(semantic)

        return _PAGE_HEAD + body + _PAGE_TAIL

    @app.get("/neighbors", response_class=HTMLResponse)
    def neighbors_page(
        session_id: str = Query(..., description="session whose neighbors to list"),
        days: float = Query(3.0, gt=0, le=365),
    ) -> str:
        rows = find_neighbors(db_path, session_id=session_id, window_days=days)
        sid = html.escape(session_id)
        body = f"<h2>neighbors of {sid}</h2>"
        body += f'<p><a href="/">← back to search</a> · window ±{days:g} days</p>'
        if not rows:
            body += (
                f'<p class="empty">±{days:g}일 내 반대 소스(학습↔작업) neighbor 없음 '
                "(또는 session_id 미존재).</p>"
            )
            return _PAGE_HEAD + body + _PAGE_TAIL
        for n in rows:
            title = html.escape(str(n.get("title") or ""))
            nsid = html.escape(n.get("session_id") or "")
            nsource = html.escape(n.get("source") or "")
            delta = n.get("time_delta_days", 0.0)
            anchor = html.escape(str(n.get("anchor_timestamp") or ""))
            body += (
                '<div class="hit">'
                f'<div class="meta">{delta:+.2f}d · source={nsource} · '
                f"session={nsid} · anchor={anchor}</div>"
                f"<div>{title}</div>"
                "</div>"
            )
        return _PAGE_HEAD + body + _PAGE_TAIL

    @app.get("/session", response_class=HTMLResponse)
    def session_page(
        session_id: str = Query(..., description="session to read in full"),
        hl: str = Query("", description="turn_id to highlight (the search hit)"),
    ) -> str:
        s = get_session_turns(db_path, session_id)
        if s is None:
            body = (
                f'<p class="empty">세션 {html.escape(session_id)} 을(를) 찾을 수 없습니다.</p>'
                '<p><a href="/">← back to search</a></p>'
            )
            return _PAGE_HEAD + body + _PAGE_TAIL

        title = html.escape(str(s.get("title") or ""))
        source = html.escape(s.get("source") or "")
        sid = html.escape(session_id)
        body = f"<h2>{title}</h2>"
        body += (
            f'<p class="meta">source={source} · session={sid} · {len(s["turns"])} turns · '
            f'<a href="/">← back to search</a> · '
            f'<a href="/neighbors?session_id={sid}">↔ neighbors</a></p>'
        )
        parts = ['<div class="ctx">']
        for t in s["turns"]:
            is_hit = hl and t.get("turn_id") == hl
            marker = "► " if is_hit else "  "
            role = html.escape(t.get("role") or "")
            cls = "row hit" if is_hit else "row"
            foldable = (t.get("role") == "assistant") and not is_hit
            body_text = _turn_text(t.get("text") or "", t.get("role") or "", foldable=foldable)
            parts.append(f'<div class="{cls}">{marker}{role}: {body_text}</div>')
        parts.append("</div>")
        body += "".join(parts)
        return _PAGE_HEAD + body + _PAGE_TAIL

    return app
