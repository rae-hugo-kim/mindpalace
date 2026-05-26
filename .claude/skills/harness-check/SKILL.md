---
name: harness-check
allowed-tools: Bash(node:*), Bash(bash:*), Bash(cat:*), Bash(git:*), Read
argument-hint: [--dry-run] [--audit]
description: Check harness version drift and auto-sync from the source remote. Use when the user says "harness-check", "harness version", "하네스 버전", or wants to retrofit/update harness files from the source repo.
---

# Harness Check - Version Drift + Auto-Sync

## Goal

One command that both **reports drift** and **resolves it** by overwriting local harness files from the source remote. Remote wins unconditionally.

## Inputs

- `$ARGUMENTS`:
  - (empty) — check + sync (default)
  - `--dry-run` — show what would be overwritten, no changes
  - `--audit` — also run a deterministic 7-category quality audit after sync

## Constraints

| Rule | Rationale |
|------|-----------|
| Source repo self-skip | If `origin` remote matches `rae-hugo-kim/claude`, this IS the source — nothing to do |
| Remote wins | Local tuning is explicitly out of scope; overwrite without merge |
| Whitelist only | Only harness asset paths are overwritten — user code (`docs/`, `src/`, etc.) is never touched |
| Preserve `bootstrapped_at` | Keep the original first-registration timestamp |

## Process

### 1. Detect mode

```bash
cat .claude/hooks/harness/harness-meta.json 2>/dev/null || echo "missing"
git remote get-url origin
```

| Mode | Condition |
|------|-----------|
| **source repo** | `origin` URL matches `rae-hugo-kim/claude` |
| **unregistered** | meta has no `source_remote` field (and origin doesn't match source) |
| **registered** | meta has `source_remote` field |

### 2. Run the sync script

```bash
bash scripts/harness-sync.sh [--dry-run]
```

The script:
- Self-skips in the source repo
- Falls back to `git@github.com:rae-hugo-kim/claude.git` if no `source_remote` (unregistered case)
- Fetches the latest `harness/*` tag from remote
- Shallow-clones that tag into a temp dir
- Overwrites whitelist paths (`rules/`, `checklists/`, `templates/`, `CLAUDE.md`, `.claude/hooks/harness/`, `.claude/settings.json`, `.githooks/post-commit`, `scripts/harness-*.sh`, harness skill dirs)
- Rewrites `harness-meta.json` with new version/SHA + preserved `bootstrapped_at`
- Clears the SessionStart cache

### 3. Report

| Outcome | Report |
|---------|--------|
| Source repo | "Source harness repo — no sync needed" |
| Unregistered → synced | "Retrofitted to harness/<version> from default source" |
| Registered, up to date | "Harness was already at latest (harness/<version>) — files re-synced anyway" |
| Registered, drift → synced | "Synced local <old> → remote <new>" |
| `--dry-run` | List of paths that would be overwritten |
| Network failure | "Could not reach remote. Check `source_remote` URL and network" |

## Verification

```bash
cat .claude/hooks/harness/harness-meta.json
git status --short
```

Confirm `version`, `commit_sha`, `updated` reflect the remote's latest; review changes before committing.

### 4. Quality audit (when `--audit` flag passed)

After sync (or instead of it, if invoked separately), run the deterministic quality scorer:

```bash
bash scripts/harness-audit.sh           # full breakdown
bash scripts/harness-audit.sh --terse   # one-line per category + TOTAL
```

Outputs 7 categories × 0..10 (total 0..70):
- `tool_coverage`, `context_efficiency`, `quality_gates`, `memory_persistence`,
  `eval_coverage`, `security_guardrails`, `cost_efficiency`

Use the score to track harness quality across versions and to surface concrete gaps (each missing item is listed with its category).

## Error Handling

| Condition | Action |
|-----------|--------|
| `git clone` fails | Report network/auth error; do not touch local files |
| No `harness/*` tags on remote | Report error; do not touch local files |
| Source repo detected | Self-skip, exit 0 |
| Dry-run flag | Show paths, exit before any write |

## Notes

- This skill does **not** commit the synced files. After sync, review with `git status` and commit when ready.
- For scheduled drift detection (no sync), the SessionStart hook `harness-version-check.mjs` continues to report drift at session start without acting.
