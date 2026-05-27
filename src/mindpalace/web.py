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

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from mindpalace.embedding import embed_chunk
from mindpalace.search import DEFAULT_CONFIDENCE_THRESHOLD, search as search_chunks

_PAGE_HEAD = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mindpalace</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;line-height:1.5}
 form{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.5rem}
 input[type=text]{flex:1;min-width:14rem;padding:.5rem;font-size:1rem}
 select,input[type=number]{padding:.5rem}
 button{padding:.5rem 1rem;font-size:1rem;cursor:pointer}
 .hit{border:1px solid #ddd;border-radius:8px;padding:.75rem 1rem;margin:.75rem 0}
 .hit.low{border-color:#e0b000;background:#fffdf3}
 .meta{color:#666;font-size:.85rem;margin-bottom:.35rem}
 .warn{color:#b35900;font-weight:600}
 .empty{color:#666}
</style></head><body>
<h1>mindpalace</h1>
"""

_PAGE_TAIL = "</body></html>"


def _form(q: str = "", source: str = "", top_k: int = 5) -> str:
    qs = html.escape(q)
    code_sel = " selected" if source == "code" else ""
    chat_sel = " selected" if source == "chat" else ""
    return f"""<form action="/search" method="get">
 <input type="text" name="q" value="{qs}" placeholder="자연어로 검색…" autofocus>
 <select name="source">
  <option value="">all sources</option>
  <option value="code"{code_sel}>code</option>
  <option value="chat"{chat_sel}>chat</option>
 </select>
 <input type="number" name="top_k" value="{int(top_k)}" min="1" max="50" title="top_k">
 <button type="submit">search</button>
</form>"""


def _render_hit(i: int, hit: dict) -> str:
    title = html.escape(str(hit.get("title") or ""))
    text = html.escape(hit.get("text") or "")
    role = html.escape(hit.get("role") or "")
    source = html.escape(hit.get("source") or "")
    low = hit.get("low_confidence")
    cls = "hit low" if low else "hit"
    warn = ' <span class="warn">⚠ low-confidence</span>' if low else ""
    return (
        f'<div class="{cls}">'
        f'<div class="meta">[{i}] distance={hit["distance"]:.4f} · '
        f"source={source} · role={role} · title={title}{warn}</div>"
        f"<div>{text}</div>"
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
    ) -> str:
        body = _form(q=q, source=source, top_k=top_k)

        if not q.strip():
            body += '<p class="empty">쿼리를 입력하세요.</p>'
            return _PAGE_HEAD + body + _PAGE_TAIL

        results = search_chunks(
            db_path,
            q,
            embed_chunk,
            top_k=top_k,
            confidence_threshold=min_confidence,
            where_source=source or None,
        )

        if not results:
            body += (
                '<p class="empty">결과 없음 (0 hits) — 소스 필터를 해제하거나 '
                "쿼리를 넓혀 보세요.</p>"
            )
        else:
            if all(r["low_confidence"] for r in results):
                body += (
                    f'<p class="warn">high-confidence 매치 없음 — 아래 '
                    f"{len(results)}건은 best-effort(모두 low-confidence)입니다.</p>"
                )
            else:
                body += f"<p>{len(results)} hits</p>"
            body += "".join(_render_hit(i, h) for i, h in enumerate(results, start=1))

        return _PAGE_HEAD + body + _PAGE_TAIL

    return app
