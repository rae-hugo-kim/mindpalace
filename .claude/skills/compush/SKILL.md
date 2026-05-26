---
name: compush
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git push:*), Bash(git remote:*), Bash(git diff:*), Bash(git log:*), Bash(git stash:*), Bash(git check-ignore:*)
argument-hint: [repo-url]
description: Stages, commits, and pushes all changes with an auto-generated commit message. Use when the user says "compush", "커밋", "푸시해", "변경사항 올려", or wants quick commits without PR.
---

# Compush - Automatic Commit and Push

## Goal

Stage, commit, and push changes safely with a concise English commit message.

## Inputs

- `$ARGUMENTS`: Repository URL (optional). If provided, set/verify remote origin.

## Constraints

| Rule | Rationale |
|------|-----------|
| Respect .gitignore | Never stage ignored files |
| No secrets | Abort if sensitive files detected |
| No force push | Never use `--force` |
| Confirm risky push | Ask before pushing to main/master |

## Process

### 1. Pre-flight checks

```bash
git status
git diff --stat
```

Check for:
- Any changes exist?
- Sensitive files? (`.env`, `*secret*`, `*.key`, `*.pem`)
- Large files (>10MB)?
- Merge conflict markers?

### 2. Remote verification (if URL provided)

```bash
git remote -v
```

If remote differs from provided URL → ask user for action.

**HTTPS to SSH conversion**:
`https://github.com/user/repo` → `git@github.com:user/repo.git`

### 3. Stage changes

```bash
git add -A
git diff --cached --name-only
```

If sensitive files detected → unstage and abort.

### 4. Generate commit message

Format: `<type>: <short description>`

**Types**: feat, fix, refactor, docs, style, test, chore

**Rules**:
- Imperative mood ("add" not "added")
- Under 50 characters
- No period at end

### 5. Risk assessment

| Risk | Detection | Action |
|------|-----------|--------|
| Push to main/master | Branch check | Confirm with user |
| Large commit (>20 files) | File count | Warn, ask to proceed |
| Behind remote | git status | Require pull first |

### 6. Commit and push

```bash
git commit -m "<message>"
git push --follow-tags
```

`--follow-tags` ensures any annotated tags created by hooks (e.g., harness version bump) are pushed with the branch in one operation.

### 7. Output

Show:
- Files committed (count + summary)
- Commit message used
- Push result
- Remote URL

## Verification

```bash
git status
git log -1 --oneline
```

Confirm working tree clean and commit exists.

## Error Handling

| Condition | Action |
|-----------|--------|
| No changes | Report and exit |
| Sensitive file | List files, abort |
| Push rejected (non-ff) | Suggest `git pull --rebase` |
| Push rejected (auth) | Suggest SSH key check |
| Behind remote | Require pull first |
| Detached HEAD | Warn, suggest creating branch |
