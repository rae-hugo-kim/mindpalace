# CLAUDE.md (Agent Rules - Layered)

This file is **always-on** agent policy. Keep it short.

## Navigation

- Start here, then use indexes:
  - `INDEX.md`
  - `rules/INDEX.md`
  - `checklists/INDEX.md`
  - `templates/INDEX.md`

## Scope

- This policy applies to this repo/workspace when the agent is active.
- If a linked module conflicts with this file, **this file wins**.
- **This policy complements oh-my-claudecode global rules** (not replaces them).

## oh-my-claudecode Integration

This repo assumes **oh-my-claudecode** is active globally. The following are enforced automatically:

| What | How | Hook Location |
|------|-----|---------------|
| Code changes | Delegated to executor agents | N/A (global rule) |
| Scope enforcement | `scope-gate` hook | `.claude/hooks/harness/` |
| Pre-edit file read | `context-gate` + `read-tracker` hooks | `.claude/hooks/harness/` |
| Completion verification | Architect agent | N/A (global rule) |
| Backpressure on failures | `backpressure-gate` + `backpressure-tracker` hooks | `.claude/hooks/harness/` |
| Acceptance criteria | `acceptance-gate` hook | `.claude/hooks/harness/` |
| New work detection | `kickoff-detector` hook | `.claude/hooks/harness/` |

All hooks are registered in `.claude/settings.json` and included in this repo.

**What this file adds**: Project-specific constraints, evidence standards, and documentation requirements.

Harness verification contract details: [`rules/harness_integration_contract.md`](rules/harness_integration_contract.md)

## Terminology (RFC 2119)

- **MUST**: required. If you cannot comply, follow the Exception Protocol.
- **SHOULD**: default expectation; may be skipped with a short rationale.
- **MAY**: optional.

## Priority Order (Conflict Resolution)

1) **Safety & Security**
2) **Repo Truth** (lockfiles / manifests / CI / repo docs)
3) **Verification** (tests/evals/replicable steps)
4) **Change Control** (minimal change, scoped diffs)
5) **Maintainability** (readability, tidy refactors)

## Core Principles

### 1. Think Before Coding
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- → Detail: [`rules/anti_hallucination.md`](rules/anti_hallucination.md)

### 2. Simplicity First
- No features beyond what was asked. No abstractions for single-use code.
- If you write 200 lines and it could be 50, rewrite it.
- Self-check: "Would a senior engineer say this is overcomplicated?"
- → Detail: [`rules/change_control.md`](rules/change_control.md)

### 3. Surgical Changes
- Edit only lines that trace directly to the user's request.
- Match existing style. Don't "improve" adjacent code.
- If you notice unrelated issues, mention them — don't fix them.
- → Detail: [`rules/change_control.md`](rules/change_control.md)

### 4. Goal-Driven Execution
- Transform vague tasks into verifiable goals with success criteria.
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- Each step should have: [action] → verify: [check]
- → Detail: [`rules/verification_tests_and_evals.md`](rules/verification_tests_and_evals.md), [`rules/tdd_policy.md`](rules/tdd_policy.md)

## Non-Negotiables (MUST)

- **No guessing**: do not invent versions, commands, APIs, or files.
- **Repo commands**: do not guess build/test/lint/typecheck/e2e/eval commands. Discover them.
- **Risky actions**: require explicit approval before proposing/executing risky changes.
- **Verification**: every user-impacting change must include at least one reproducible verification artifact.
- **Docs/policy-only mode**: for pure markdown/policy/template edits, follow the docs-only verification path in `rules/verification_tests_and_evals.md` and include its required evidence format.
- **Evidence**: cite concrete evidence for key decisions (file paths + excerpts or command output).
- **Reference doc sync**: in the same PR, update `claudedocs/CLAUDEKR.md` and `claudedocs/CLAUDE_original.md` or explicitly mark them as stale.

## Completion Contract (MUST)

When claiming a task is "done", the final message MUST include:

- **Applied rules**: which rules/checklists were applied
- **Evidence**: concrete evidence for key claims (file paths + excerpts or command outputs)
- **Verification**: what was run/done to verify (commands/results)

**Note**: Architect verification is handled by oh-my-claudecode global rules. This contract defines the *content* of the completion report.

## Exception Protocol (MUST when blocked)

If you cannot comply with any MUST:

1) State **why** (what constraint prevents compliance).
2) Provide **2–3 alternatives** (safe options only).
3) Ask for **explicit confirmation** if any alternative is risky or irreversible.

## MCP Server Policy (Trigger-based)

- See [`rules/mcp_policy.md`](rules/mcp_policy.md) for full policies on all MCP servers.
- **Context7**: MUST use for new external APIs/SDKs, dependencies, version-sensitive syntax.
- **Serena**: SHOULD use for symbol navigation, refactoring. MUST use `--context claude-code` flag.
- **Supabase**: MUST use migrations for DDL; MAY use direct SQL for queries.
- **Web Search**: SHOULD use for current events, errors, latest docs.

## Agent Routing Policy (Trigger-based)

- See [`rules/agent_routing.md`](rules/agent_routing.md) for full routing rules.
- **researcher** (Exa): SHOULD delegate for external docs, web search, error lookups.
- **db-worker** (Supabase): MUST delegate for DDL changes and schema operations.
- **refactorer** (Serena): SHOULD delegate for 3+ file symbol renames or impact analysis.
- **full-context** (all MCP): SHOULD delegate when 2+ MCP domains intersect in one task.
- **reviewer**: SHOULD delegate for code changes ≥10 lines or logic changes. 3-pass adversarial (self + Codex + OMC).
- **verifier**: MUST delegate before claiming task completion when AC exists.

## Linked Modules

- Safety & security: [`rules/safety_security.md`](rules/safety_security.md)
- Anti-hallucination & evidence: [`rules/anti_hallucination.md`](rules/anti_hallucination.md)
- Repo command discovery: [`rules/repo_command_discovery.md`](rules/repo_command_discovery.md)
- MCP server policies: [`rules/mcp_policy.md`](rules/mcp_policy.md)
- Context7 trigger policy: [`rules/context7_policy.md`](rules/context7_policy.md)
- Verification (tests + evals): [`rules/verification_tests_and_evals.md`](rules/verification_tests_and_evals.md)
- Change control (minimal change, scope, tidy): [`rules/change_control.md`](rules/change_control.md)
- Documentation policy (optional): [`rules/documentation_policy.md`](rules/documentation_policy.md)
- Assetization (spec/decision/retro): [`rules/assetization.md`](rules/assetization.md)
- Commit/PR discipline: [`rules/commit_and_pr.md`](rules/commit_and_pr.md)
- TDD policy: [`rules/tdd_policy.md`](rules/tdd_policy.md)
- Harness integration contract: [`rules/harness_integration_contract.md`](rules/harness_integration_contract.md)
- Code review policy: [`rules/code_review_policy.md`](rules/code_review_policy.md)
- Quality gates: [`rules/quality_gates.md`](rules/quality_gates.md)
- Context management: [`rules/context_management.md`](rules/context_management.md)
- Cost awareness: [`rules/cost_awareness.md`](rules/cost_awareness.md)
- Learning policy: [`rules/learning_policy.md`](rules/learning_policy.md)
- Coding standards: [`rules/coding_standards.md`](rules/coding_standards.md)
- Documentation standards: [`rules/doc_standards.md`](rules/doc_standards.md)
- Agent security: [`rules/agent_security.md`](rules/agent_security.md)
- Hook recipes: [`rules/hook_recipes.md`](rules/hook_recipes.md)
- Session persistence: [`rules/session_persistence.md`](rules/session_persistence.md)
- Adversarial review: [`rules/adversarial_review.md`](rules/adversarial_review.md)
- Agent routing: [`rules/agent_routing.md`](rules/agent_routing.md)

## Checklists (Use as needed)

- Planning: [`checklists/plan.md`](checklists/plan.md)
- Verification: [`checklists/verify.md`](checklists/verify.md)
- Risky actions: [`checklists/risky_actions.md`](checklists/risky_actions.md)
- Bugfix protocol: [`checklists/bugfix.md`](checklists/bugfix.md)
- PR body: [`checklists/pr.md`](checklists/pr.md)
- Code review: [`checklists/code_review.md`](checklists/code_review.md)
- Quality gate: [`checklists/quality_gate.md`](checklists/quality_gate.md)
- Eval (EDD): [`checklists/eval.md`](checklists/eval.md)
- Research before implement: [`checklists/research_before_implement.md`](checklists/research_before_implement.md)

## Templates

- Assumptions: [`templates/assumptions.md`](templates/assumptions.md)
- Change log: [`templates/decision_log.md`](templates/decision_log.md)
- PR description: [`templates/pr_body.md`](templates/pr_body.md)
- Retro note: [`templates/retro.md`](templates/retro.md)
- Eval definition: [`templates/eval_definition.md`](templates/eval_definition.md)
- Eval report: [`templates/eval_report.md`](templates/eval_report.md)
- Session retro: [`templates/session_retro.md`](templates/session_retro.md)
