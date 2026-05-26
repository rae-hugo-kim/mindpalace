# Tidying Catalog

Apply patterns in order of safety (safest first).

## Level 1: Safe (No Logic Change)

| Pattern | Before | After |
|---------|--------|-------|
| **Dead code removal** | Unused imports, variables, functions | Remove completely |
| **Normalize whitespace** | Inconsistent spacing | Consistent formatting |
| **Reorder declarations** | Random order | Logical grouping |
| **Rename for clarity** | `x`, `data`, `tmp` | Intention-revealing names |

**Risk**: Virtually none. Can be applied freely.

## Level 2: Low Risk (Structure Only)

| Pattern | Before | After |
|---------|--------|-------|
| **Guard clauses** | Nested if-else | Early returns |
| **Extract constant** | Magic numbers/strings | Named constants |
| **Normalize symmetries** | Inconsistent patterns | Uniform structure |
| **Collapse nesting** | Deep indentation | Flattened logic |

**Risk**: Low. Structure changes but logic is equivalent.

## Level 3: Medium Risk (Careful Review)

| Pattern | Before | After |
|---------|--------|-------|
| **Extract helper** | Repeated code block | Single function |
| **Inline trivial** | One-line wrapper | Direct call |
| **Split phase** | Mixed concerns | Separated stages |
| **Move code** | Misplaced logic | Cohesive location |

**Risk**: Medium. Requires careful verification. May affect call sites.

## Application Order

1. Apply all Level 1 patterns first
2. Then Level 2 patterns
3. Level 3 only with explicit approval
4. **Never skip levels**

## Analyze Checklist

| Check | Level | Found? |
|-------|-------|--------|
| Dead code (unused imports/vars/functions) | 1 | |
| Poor naming (`x`, `data`, `tmp`) | 1 | |
| Deep nesting (>3 levels) | 2 | |
| Magic values (hardcoded numbers/strings) | 2 | |
| Repeated patterns (≥2 occurrences) | 3 | |
| Mixed concerns (multiple responsibilities) | 3 | |
