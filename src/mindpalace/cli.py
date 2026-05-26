"""mindpalace CLI: ``import`` and ``search``.

Two commands wire the existing modules into a usable entry point:

- ``mindpalace import <path> --source code|chat --db <path>``: parse the
  given file with the matching parser, then call ``store_session`` for
  each session. Counts (sessions_inserted, chunks_inserted, dedup_skipped)
  are printed at the end.
- ``mindpalace search <query> --db <path> [--top-k N]``: embed the query
  and print the top-k chunks (chunk_id, distance, role, title, text).

The CLI deliberately stays thin — no business logic lives here. It's a
demo entry point so the walking skeleton can be driven against real data
from a shell.
"""
from __future__ import annotations

from pathlib import Path

import typer

from mindpalace.embedding import embed_chunk
from mindpalace.parsing import parse_chat_json, parse_claude_code_jsonl
from mindpalace.search import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    get_chunk_context,
    search as search_chunks,
)
from mindpalace.storage import init_db, store_session

app = typer.Typer(add_completion=False, help="Mindpalace personal knowledge vault.")

_TEXT_PREVIEW_CHARS = 160


@app.command("import")
def import_cmd(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Source file path."),
    source: str = typer.Option(..., "--source", "-s", help="One of: code, chat."),
    db: Path = typer.Option(..., "--db", help="SQLite DB path (created if missing)."),
) -> None:
    """Parse and store a session file."""
    if source not in {"code", "chat"}:
        typer.echo(f"error: --source must be 'code' or 'chat', got {source!r}", err=True)
        raise typer.Exit(code=2)

    init_db(str(db))

    if source == "code":
        sessions = [parse_claude_code_jsonl(str(path))]
    else:
        sessions = parse_chat_json(str(path))

    total_sessions = 0
    total_chunks = 0
    total_dedup = 0
    for sess in sessions:
        counts = store_session(str(db), sess, source, embed_chunk)
        total_sessions += counts["sessions_inserted"]
        total_chunks += counts["chunks_inserted"]
        total_dedup += counts["dedup_skipped"]

    typer.echo(
        f"imported source={source} file={path} "
        f"sessions_inserted={total_sessions} "
        f"chunks_inserted={total_chunks} "
        f"dedup_skipped={total_dedup}"
    )


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Natural-language query."),
    db: Path = typer.Option(..., "--db", help="SQLite DB path."),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results."),
    min_confidence: float = typer.Option(
        DEFAULT_CONFIDENCE_THRESHOLD,
        "--min-confidence",
        help="L2 distance cut-off; hits above this are marked low-confidence.",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        help="Restrict to a single source (e.g. 'code' or 'chat').",
    ),
    context: int = typer.Option(
        0,
        "--context",
        "-c",
        help="Show ±N surrounding turns from the same session under each hit.",
    ),
) -> None:
    """Run a semantic search over stored chunks."""
    results = search_chunks(
        str(db),
        query,
        embed_chunk,
        top_k=top_k,
        confidence_threshold=min_confidence,
        where_source=source,
    )

    if not results:
        typer.echo("no results (0 hits) — try removing filters or broadening the query.")
        return

    if all(r["low_confidence"] for r in results):
        typer.echo(
            f"no high-confidence matches for: {query}\n"
            f"  showing top {len(results)} best-effort results below (all low-confidence)."
        )
    else:
        typer.echo(f"{len(results)} hits for: {query}")

    for i, hit in enumerate(results, start=1):
        text = (hit["text"] or "").replace("\n", " ")
        if len(text) > _TEXT_PREVIEW_CHARS:
            text = text[:_TEXT_PREVIEW_CHARS] + "…"
        marker = "⚠ " if hit["low_confidence"] else "  "
        typer.echo(
            f"{marker}[{i}] distance={hit['distance']:.4f} "
            f"source={hit['source']} role={hit['role']} "
            f"title={hit['title']!r}\n      {text}"
        )
        if context > 0:
            session_id = hit["session_id"]
            turn_id = hit["chunk_id"][len(session_id) + 1 :]
            for ctx in get_chunk_context(str(db), session_id, turn_id, window=context):
                ctx_text = (ctx["text"] or "").replace("\n", " ")
                if len(ctx_text) > _TEXT_PREVIEW_CHARS:
                    ctx_text = ctx_text[:_TEXT_PREVIEW_CHARS] + "…"
                arrow = "►" if ctx["is_hit"] else " "
                typer.echo(f"        {arrow} {ctx['role']:>9}: {ctx_text}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
