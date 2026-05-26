# INDEX.md (rules)

## Ownership legend

- `owner: global-harness` → enforced by oh-my-claudecode platform/harness.
- `owner: local-policy` → enforced by this repository’s policy docs and review process.
- Any `MUST` without an explicit owner tag defaults to `owner: local-policy` unless explicitly stated otherwise.

## Conflict resolution order (when global and local diverge)

1. **System/developer/user instructions** (runtime prompt instructions)
2. **Global harness requirements** (`owner: global-harness`)
3. **Repository-local policy** (`owner: local-policy`)
4. **Advisory guidance** (`SHOULD` / `MAY`)

If a local policy conflicts with a global harness rule, follow the global harness rule and document the deviation.
If both global and local guidance exist for the same tool choice, apply global-harness rules first, then local policy ordering.

## Core rails

- Safety & security (hard rails): [`safety_security.md`](safety_security.md)
- Agent security (adversarial threats, prompt injection defense): [`agent_security.md`](agent_security.md)
- Anti-hallucination & evidence ladder: [`anti_hallucination.md`](anti_hallucination.md)
- Repo command discovery (never guess commands): [`repo_command_discovery.md`](repo_command_discovery.md)

## Quality rails

- Coding standards (immutability, file limits, input validation): [`coding_standards.md`](coding_standards.md)
- Verification (tests + evals + EDD): [`verification_tests_and_evals.md`](verification_tests_and_evals.md)
- Change control (minimal change, scope, Tidy First triggers): [`change_control.md`](change_control.md)
- TDD policy (RED → GREEN → TIDY): [`tdd_policy.md`](tdd_policy.md)
- Code review policy (severity, thresholds, confidence gating): [`code_review_policy.md`](code_review_policy.md)
- Quality gates (FORMAT/LINT/TYPECHECK/TEST/BUILD/EVAL): [`quality_gates.md`](quality_gates.md)

## Tool rails

- MCP server policies (when/how to use): [`mcp_policy.md`](mcp_policy.md)
- Context7 policy (trigger-based): [`context7_policy.md`](context7_policy.md)
- Hook recipes (concrete hook implementations): [`hook_recipes.md`](hook_recipes.md)

## Process rails

- Assetization (spec/decision/retro): [`assetization.md`](assetization.md)
- Commit & PR discipline: [`commit_and_pr.md`](commit_and_pr.md)
- Harness integration contract: [`harness_integration_contract.md`](harness_integration_contract.md)

## Operational rails

- Context management (compaction, phase transitions): [`context_management.md`](context_management.md)
- Session persistence (cross-session state, context loading): [`session_persistence.md`](session_persistence.md)
- Cost awareness (model selection, token efficiency): [`cost_awareness.md`](cost_awareness.md)
- Learning policy (when/how to capture learnings): [`learning_policy.md`](learning_policy.md)

## Optional

- Documentation policy (language, README vs INDEX, latest-only option): [`documentation_policy.md`](documentation_policy.md)

