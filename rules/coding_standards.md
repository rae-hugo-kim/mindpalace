# Coding Standards

<!-- Inspired by ECC coding-style and patterns rules. Covers code shape constraints complementing change_control.md (process/scope). -->

## Purpose

Enforceable code shape constraints that prevent quality drift. These are language-agnostic — language-specific rules belong in project-level `.claude/rules/`.

---

## MUST: Immutability by default

Always create new objects or values; never mutate existing ones in-place.

- Return new copies with changes applied, not modified originals.
- Use spread/copy idioms or immutable data structures where the language provides them.
- Exceptions: performance-critical hot paths (document why mutation is necessary).

Rationale: Immutable data prevents hidden side effects, simplifies debugging, and enables safe concurrency.

---

## MUST: Input validation at system boundaries

Validate all data crossing a trust boundary before processing:

- User input (forms, CLI arguments, query parameters)
- External API responses
- File content from untrusted sources
- Environment variables used for configuration

Use schema-based validation where available. Fail fast with clear error messages.

Internal function calls between trusted modules do NOT need redundant validation.

---

## MUST: Explicit error handling

- Never silently swallow errors (empty catch blocks, ignored return codes).
- Log detailed error context server-side (stack trace, input values, timestamp).
- Provide user-friendly messages client-side (no raw stack traces or internal IDs).
- Propagate or wrap errors — do not discard them.

---

## SHOULD: File size limits

- **Typical**: 200–400 lines per file.
- **Maximum**: 800 lines. Beyond this, extract a focused module.
- Measure by logical content, not comments or blank lines.

---

## SHOULD: Function size limits

- **Maximum**: 50 lines per function/method.
- If a function exceeds this, extract helper functions or decompose the logic.

---

## SHOULD: Nesting depth limit

- **Maximum**: 4 levels of indentation.
- Use early returns, guard clauses, or extracted functions to reduce nesting.

---

## SHOULD: Feature/domain organization

Organize code by feature or domain, not by type:

```
PREFER:  src/auth/login.ts, src/auth/session.ts
AVOID:   src/controllers/auth.ts, src/services/auth.ts, src/models/auth.ts
```

Exception: Small projects where type-based organization is simpler.

---

## SHOULD: No hardcoded values

Use constants, configuration, or environment variables instead of magic numbers and inline strings.

---

## Self-Check

Before marking code complete:

- [ ] No in-place mutations (immutable patterns used)?
- [ ] Input validation at every system boundary?
- [ ] All errors handled explicitly (no empty catch blocks)?
- [ ] All files under 800 lines?
- [ ] All functions under 50 lines?
- [ ] No nesting deeper than 4 levels?
- [ ] No hardcoded magic values?
