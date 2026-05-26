# Context7 Policy (Trigger-Based)

## MUST: use Context7 when the risk is real

You MUST use Context7 when any of the following is true:

- You are introducing a **new dependency** or changing dependency versions in a meaningful way
- You are using an **external API/SDK** that is not already used in the repo
- The change depends on **version-specific syntax** or potentially deprecated behavior
- You are resolving an error that likely depends on library/framework semantics

## MAY: skip Context7 for in-repo established patterns

You MAY skip Context7 when:

- The repo already contains the same API usage pattern and you are doing a small extension/modification
- The change is purely internal (no new external/library surface)

When skipping, you SHOULD cite the in-repo evidence (file path + snippet).

## MUST: do not invent undocumented behavior

If Context7 is required but unavailable:

- Follow the Exception Protocol (state what is blocked, provide safe alternatives, ask for confirmation).




