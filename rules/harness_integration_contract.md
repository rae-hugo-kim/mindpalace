# Harness Integration Contract

This document defines the repo-level contract for validating harness integration before an agent claims policy compliance.

## Hook Location

All hooks are in `.claude/hooks/harness/` and registered in `.claude/settings.json`.
Runtime state is stored in `.omc/harness-state/` (project-local, gitignored).

## Required Gates and Hook Names

The following controls are required when harness is available:

1. `scope-gate` hook — blocks edits to out-of-scope paths (PreToolUse: Edit|Write)
2. `context-gate` hook — blocks edits to unread files (PreToolUse: Edit|Write)
3. `read-tracker` hook — records file reads for context-gate (PostToolUse: Read)
4. `acceptance-gate` hook — blocks commits with unmet acceptance criteria (PreToolUse: Bash)
5. `backpressure-gate` hook — blocks commits if build/test/lint failed (PreToolUse: Bash)
6. `backpressure-tracker` hook — records build/test/lint results (PostToolUse: Bash)
7. `kickoff-detector` hook — reminds about kickoff for new work (UserPromptSubmit)
8. Architect verification — independent completion verification (oh-my-claudecode agent)

## Gate Verification Requirements

Use concrete checks, not assumptions.

### 1) `scope-gate`

- File: `.claude/hooks/harness/scope-gate.mjs`
- Log: `.omc/harness-state/hook-debug.log`
- Reads: `docs/harness/seed.yaml` (out_of_scope) or `docs/harness/current-scope.md`

### 2) `context-gate` + `read-tracker`

- Files: `.claude/hooks/harness/context-gate.mjs`, `.claude/hooks/harness/read-tracker.mjs`
- Log: `.omc/harness-state/hook-debug.log`
- State: `.omc/harness-state/read-log.txt`

### 3) `acceptance-gate`

- File: `.claude/hooks/harness/acceptance-gate.mjs`
- Log: `.omc/harness-state/hook-debug.log`
- Reads: `docs/harness/current-scope.md` (checkboxes), `docs/harness/seed.yaml` (AC), `docs/harness/acceptance-done` (override flag)

### 4) `backpressure-gate` + `backpressure-tracker`

- Files: `.claude/hooks/harness/backpressure-gate.mjs`, `.claude/hooks/harness/backpressure-tracker.mjs`
- Log: `.omc/harness-state/hook-debug.log`
- State: `.omc/harness-state/backpressure-status`, `.omc/harness-state/test-history.json`
- **Known limitation**: `backpressure-tracker` runs on PostToolUse (success only). Claude Code does not invoke PostToolUse hooks on tool failure, so failed build/test/lint results are not recorded. `backpressure-gate` can only verify the presence of recent success, not detect failures directly.

### 5) `kickoff-detector`

- File: `.claude/hooks/harness/kickoff-detector.mjs`
- Reads: `docs/harness/kickoff-done` (suppresses reminder if exists)

### 6) Architect verification + Completion Attack Gate

- Provided by oh-my-claudecode `architect` agent
- Not a file hook — invoked via agent delegation
- **Extended by completion-attack gate** (see [`rules/adversarial_review.md`](adversarial_review.md)):
  - architect (기존 역할 유지) + security-reviewer + test-engineer 병렬 실행
  - 불일치 시 critic이 합의 판정
  - CRITICAL 발견 시 블로킹
- Output: `docs/harness/completion-attack-report.md`

## Startup Checklist (Run Before Claiming Compliance)

1. Confirm hooks directory exists: `test -d .claude/hooks/harness && echo hooks_ok`
2. Confirm all hook files are present:
   ```bash
   for h in scope-gate context-gate read-tracker acceptance-gate backpressure-gate backpressure-tracker kickoff-detector; do
     test -f ".claude/hooks/harness/$h.mjs" && echo "$h: ok" || echo "$h: MISSING"
   done
   ```
3. Confirm settings.json registers hooks: `cat .claude/settings.json | grep -c "hooks/harness"` (should be 7)
4. Confirm Architect agent is available via oh-my-claudecode
5. Record harness status in your working notes and final PR report

## Fallback Behavior When a Gate Is Unavailable

If any required gate is unavailable, do not claim fully automated harness compliance for that gate. Apply this downgrade policy:

- Missing `scope-gate`:
  - Downgrade from **MUST (automated scope enforcement)** to **manual scope checklist MUST**.
  - Manually enumerate in-scope files before edits and re-check before commit.
- Missing `context-gate`:
  - Downgrade from **MUST (automated pre-read enforcement)** to **manual pre-edit read checklist MUST**.
  - Record files read before each edit batch.
- Missing `acceptance-gate`:
  - Downgrade from **MUST (automated acceptance checks)** to **manual acceptance checklist MUST**.
  - Require explicit evidence section with commands, outputs, and file citations.
- Missing `backpressure-gate`:
  - Downgrade from **MUST (automated failure pressure)** to **manual stop-and-review MUST**.
  - After any failed verification, halt feature work until failure is resolved or explicitly risk-accepted.
- Missing Architect verification:
  - Downgrade from **MUST (independent verifier)** to **manual two-pass self-review MUST**.
  - Complete a second-pass review using `checklists/verify.md` before claiming done.

When downgrading, final report MUST include:

- Which gate was unavailable
- How manual checklist substitution was applied
- Remaining residual risk

## Known-Failure Matrix

| Symptom | Likely cause | Safe mitigation |
|---|---|---|
| Hook file not found in `.claude/hooks/harness/` | Partial clone or deleted hook file | Re-clone template or restore from git; if blocked, activate manual checklist downgrade |
| Hook exists but no events in `.omc/harness-state/hook-debug.log` | Hook not registered in `.claude/settings.json` | Verify settings.json hook entries, restart session, re-run benign trigger |
| `acceptance-gate` repeatedly blocks completion | Missing evidence or unchecked AC in `current-scope.md` | Check off completed criteria or create `docs/harness/acceptance-done` override |
| `backpressure-gate` loops on failures | Underlying failing test/check never addressed | Stop retries, fix root cause, then re-run once with documented rationale |
| `context-gate` blocks unexpectedly | `read-log.txt` missing or stale | Read the file first; if persistent, check read-tracker is registered in settings.json |
| Architect log missing for completed task | oh-my-claudecode not installed or architect agent unavailable | Run manual two-pass verification and mark Architect as downgraded in report |

## Copy-Paste Verification Template

Use this in PR descriptions or completion reports:

```md
### Harness Verification
- scope-gate: [active | unavailable->manual] (evidence: `<command/log snippet>`)
- context-gate: [active | unavailable->manual] (evidence: `<command/log snippet>`)
- acceptance-gate: [active | unavailable->manual] (evidence: `<command/log snippet>`)
- backpressure-gate: [active | unavailable->manual] (evidence: `<command/log snippet>`)
- Architect verification: [active | unavailable->manual] (evidence: `<command/log snippet>`)

### Downgrades (if any)
- Gate: `<name>`
- Manual checklist used: `<checklist/steps>`
- Residual risk: `<brief note>`
```
