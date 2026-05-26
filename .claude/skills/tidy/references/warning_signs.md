# Warning Signs & Error Handling

## Warning Signs (STOP immediately)

| Warning | Action |
|---------|--------|
| Adding new functionality | STOP. This is tidying, not feature work. |
| Changing test assertions | STOP. Tests verify unchanged behavior. |
| "While I'm here..." thoughts | STOP. Scope creep alert. |
| No tests to verify | STOP. Ask user for verification strategy. |
| Refactoring untouched code | STOP. Only tidy the target. |
| Guessing a command/path | STOP. Discover from repo first. |
| Large diff accumulating | STOP. Review if minimal diff is violated. |

## Error Handling

| Condition | Action |
|-----------|--------|
| Tests fail after tidying | Revert immediately, report which tidying broke |
| No test coverage | Warn user, ask for manual verification approval |
| File not found | List similar files, ask for clarification |
| Binary/generated file | Skip with explanation |
| Merge conflicts present | Abort, resolve conflicts first |
| Unknown test command | Search repo for test config, ask user if not found |
| Frozen area touched | Abort that tidying, warn user |

## Recovery Procedures

### Test Failure After Tidying
```bash
git checkout -- <file>          # Discard change
# OR
git stash                       # Save for later analysis
```

### Multiple Tidyings, One Broke
```bash
git log --oneline -5            # Find the breaking commit
git revert <hash>               # Revert just that one
```

### Need to Undo Everything
```bash
git reflog                      # Find state before tidying
git reset --hard <ref>          # Go back to that state
```

## Red Flags in Code Review

If you see these in your tidying diff, reconsider:

- [ ] New function with business logic (not just extraction)
- [ ] Changed return values
- [ ] Modified test expectations
- [ ] New dependencies added
- [ ] Files outside the target scope
- [ ] Diff > 100 lines for a single pattern
