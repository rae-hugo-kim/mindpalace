# Tidy First Philosophy

Based on Kent Beck's "Tidy First?" (2023) and Augmented Coding principles.

## Core Principle

> "For each desired change, make the change easy (warning: this may be hard), then make the easy change."

## What is Tidying?

> "Tidying is the art of preparing code for change without changing what it does."

Tidying is **not**:
- Adding features
- Fixing bugs
- Optimizing performance
- Rewriting

Tidying **is**:
- Structural improvement
- Behavior-preserving
- Small, reversible
- Preparation for future changes

## The Goal

> "The goal is not perfect code. The goal is code that's ready for the next change."

Don't tidy for tidying's sake. Tidy because:
1. You're about to change this code
2. The current structure makes the change hard
3. Tidying will make the change easy

## Timing

**Tidy first** when:
- You're about to make a change
- The current structure is blocking you
- Tidying is cheap relative to the change

**Don't tidy** when:
- You're not going to change this code
- Tidying would be expensive
- The code is already easy to change

## The Discipline

1. **Separate structure from behavior**: Never mix in one commit
2. **Keep tests green**: Every tidying must pass tests
3. **Small steps**: Each tidying is independently revertable
4. **One pattern at a time**: Don't batch multiple patterns

## References

- Kent Beck, "Tidy First?" (2023)
- [Augmented Coding: Beyond the Vibes](https://tidyfirst.substack.com/p/augmented-coding-beyond-the-vibes)
- [Teaching Augmented Coding](https://tidyfirst.substack.com/p/teaching-augmented-coding)
