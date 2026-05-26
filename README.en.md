**[한국어](README.md)**

# mindpalace

A personal knowledge vault that makes past learning and work (Claude Code sessions, Claude web/desktop chats) retrievable even with fuzzy memory cues. Semantic search + automatic metadata extraction + a locally hosted web UI reachable from your own devices over a mesh network.

## Goal

Build v0 of a personal knowledge vault: manually import Claude Code session logs and Claude web/desktop chat sessions and preserve them as raw, auto-extract metadata (file paths, commands, tools, timestamps, headings), serve semantic search over chunks, surface results as chunk hits paired with session context, and expose the whole thing through a locally hosted web UI accessible from the owner's other devices via Tailscale/VPN mesh.

## Acceptance Criteria

- [ ] Both sources (Claude Code + web/desktop export) import and persist as raw to the DB
- [ ] Automatic metadata extraction (Code: paths/commands/tools/errors; chat: time/heading)
- [ ] Natural-language semantic search returns chunk-level matches
- [ ] Results display chunk hit + session context (hierarchical)
- [ ] Time / path / domain metadata filters work
- [ ] Weak time-and-heading-based links between learning and work sessions are surfaced
- [ ] Web UI is reachable from the owner's other devices over Tailscale mesh
- [ ] At least one end-to-end automated test on the critical path (import → embed → search) passes

## Constraints

- No automated ingest (gmail / Claude API sync) — deferred to v1+
- No heavy LLM processing at ingest time (avoid baking in the current learning level)
- Local data only — no cloud storage
- No public URL / external auth — access limited to Tailscale/VPN mesh
- Single-user only

## Status

🚧 In development — see [`docs/harness/kickoff-summary.md`](docs/harness/kickoff-summary.md) for full context.
