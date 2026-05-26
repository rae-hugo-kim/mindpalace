# Session Persistence

<!-- Inspired by ECC longform guide session storage patterns. Complements context_management.md (WHEN/WHAT to compact) with HOW/WHERE to persist and restore. -->

## Purpose

Concrete mechanisms for saving and restoring session state across compaction events and session boundaries. `context_management.md` governs when to compact and what to preserve; this file governs how to persist and where to store it.

---

## SHOULD: Structured session state files

At logical phase boundaries (see `context_management.md`), write a session state file containing:

- **What worked**: Successful approaches with evidence (file paths, test results).
- **What failed**: Attempted approaches and why they were abandoned.
- **What remains**: Pending tasks with enough context to resume without re-reading everything.

Store in `.omc/sessions/` or `.claude/sessions/`. One file per session or per major phase.

---

## SHOULD: PreCompact auto-save

Use a `PreCompact` hook to automatically save critical state before context compaction fires:

- Current task description and success criteria.
- Key file paths and their roles.
- Architecture decisions made this session.
- Active todo list state.

This prevents accidental context loss when auto-compaction triggers at an unexpected moment.

---

## SHOULD: SessionStart context loading

Use a `SessionStart` hook to automatically load relevant prior context:

- Most recent session state file (if resuming work).
- Project-specific context (detected package manager, framework, conventions).
- Pending tasks from previous session.

Keep loaded context minimal — only what's needed to resume, not full history.

---

## MAY: Dynamic system prompt injection

For mode-specific workflows, inject targeted context at session start:

```bash
# Load review-focused context
claude --system-prompt "$(cat .claude/contexts/review.md)"

# Load research-focused context
claude --system-prompt "$(cat .claude/contexts/research.md)"
```

Context files should be small (<100 lines) and focused on the specific workflow.

---

## MAY: Context aliases

Maintain named context profiles for common workflows:

| Alias | Context File | Use For |
|-------|-------------|---------|
| `dev` | `.claude/contexts/dev.md` | Active development (file paths, architecture) |
| `review` | `.claude/contexts/review.md` | Code review (standards, checklist refs) |
| `research` | `.claude/contexts/research.md` | Research mode (search patterns, MCP refs) |

---

## Relationship to Other Rules

- **`context_management.md`**: Governs WHEN to compact and WHAT to preserve. This file governs HOW and WHERE.
- **`learning_policy.md`**: Governs capturing reusable learnings. Session persistence captures transient session state.
- **`hook_recipes.md`**: Provides the hook mechanism; this file describes what to persist in those hooks.

---

## Self-Check

Before ending a session or compacting:

- [ ] Session state file written with worked/failed/remaining sections?
- [ ] PreCompact hook configured to save critical state?
- [ ] Key decisions and file paths captured (not just in conversation memory)?
