# Assetization (Spec → Implement → Retro)

## SHOULD: leave a lightweight spec for non-trivial changes

For any non-trivial change, record:

- Goal and success criteria
- Scope and non-goals
- Assumptions/constraints
- Verification plan

This can live in an issue/PR description.

## Team agreement: PRD/overview as SST + optional TL;DR (no separate 1-pager by default)

- **SST**: During development, the **source of truth is the long-form PRD/overview** (not a separate 1-pager file).
- **Default**: Do **not** create a separate 1-pager document “for insurance” by default.
- **If needed**: Add a short **TL;DR (1-pager summary) section at the top of the PRD/overview** instead of creating a new file.
  - Template: `../templates/prd_tldr_header.md`
- **Triggers to add TL;DR** (examples):
  - PRD becomes too long to onboard quickly
  - Scope drift debates repeat during implementation
  - PRD changes frequently and the team needs a stable summary snapshot at the top

## SHOULD: record decisions (why)

When a decision is not obvious, record:

- The decision
- Alternatives considered
- Evidence
- Trade-offs

Suggested home: `docs/adr/` or the PR Decision Log.

## SHOULD: retro for repeated failures

If a failure mode repeats:

- Capture what happened
- Add a trigger-based rule/checklist item to prevent recurrence

## Templates

- Assumptions: `../templates/assumptions.md`
- Decision log: `../templates/decision_log.md`
- Retro: `../templates/retro.md`


