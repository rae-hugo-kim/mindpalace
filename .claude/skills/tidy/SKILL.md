---
allowed-tools: Read, Edit, Glob, Grep, Bash(git diff:*), Bash(git status:*), Bash(npm test:*), Bash(pnpm test:*), Bash(yarn test:*), Bash(pytest:*), Bash(go test:*)
argument-hint: <file or directory>
description: Refactor code using Kent Beck's Tidy First principles
---

# Tidy - Code Refactoring (Kent Beck's Tidy First)

## Goal

Apply structural improvements to code without changing behavior.

Core philosophy: "Make the change easy, then make the easy change."

## Inputs

- `$ARGUMENTS`: Target file(s) or directory to tidy
- **(User provides)** Goal: "refactor only" vs "include narrow bug fixes"
- **(User provides)** Constraints: frozen areas, rename permission

## Non-Negotiables

| Rule | Rationale |
|------|-----------|
| **No guessing** | Discover commands/paths from repo. Never assume. |
| **Minimal diff** | No unnecessary formatting or drive-by cleanups. |
| **Verification required** | Every change needs verifiable check. |
| **Behavior unchanged** | All tests must pass. Tidying ≠ feature work. |
| **One pattern per commit** | Keep reversible. |

## Workflow

### 1. Explore
- Read `package.json` / `pyproject.toml` / `Makefile` to find test command
- `git status` to check current state
- **STOP if no verification method exists**

### 2. Pre-flight
- Run discovered test command
- **STOP if tests fail** — green baseline required

### 3. Analyze
- Read target file(s)
- Categorize by catalog levels (see `references/catalog.md`)
- Identify: dead code, poor naming, deep nesting, magic values, repeated patterns

### 4. Plan
- Present findings grouped by Level 1/2/3
- Ask: "Apply all? [Yes / Select specific / Abort]"

### 5. Implement
- One pattern at a time
- Announce → Edit → Verify → Report
- **If tests fail**: Revert immediately, do NOT continue

### 6. Record
- Output summary (see Output Format below)

## Output Format

```markdown
## Tidy Summary

### What Changed
- (3-7 bullets with file:line reference)

### Verification
- Command: `___`
- Result: ✓ Pass / ✗ Fail

### Rollback
- `git revert <hash>` or `git checkout <file>`
```

## References (load as needed)

- `references/catalog.md` — Tidying patterns by risk level
- `references/philosophy.md` — Kent Beck quotes and principles
- `references/warning_signs.md` — When to STOP
- `assets/examples/` — Before/After code examples

## Patterns Applied

`constraints_first`, `explicit_output_schema`, `reason_act_loop`, `safety_guard`, `tool_selection`
