---
name: compr
allowed-tools: Bash(git *), Bash(gh *)
argument-hint: [branch-name]
description: Creates a feature branch, commits changes, pushes, and opens a pull request. Use when the user says "compr", "PR 만들어", "풀리퀘", "PR 올려", or is ready to submit work for review.
---

# Compr - Commit and Pull Request

## Goal

Create a feature branch, commit changes, push, and open a pull request — all in one command.

## Inputs

- `$ARGUMENTS`: Branch name (optional). If not provided, auto-generate from commit type.

## Constraints

| Rule | Rationale |
|------|-----------|
| Respect .gitignore | Never stage ignored files |
| No secrets | Abort if sensitive files detected |
| No force push | Never use `--force` |
| One PR per branch | Check existing PRs first |

## Process

### 1. Pre-flight checks

```bash
git status
git diff --stat
```

Check for:
- Any changes exist?
- Sensitive files? (`.env`, `*secret*`, `*.key`, `*.pem`)
- Already on feature branch?

If no changes → abort with "Nothing to commit".

### 2. Determine target branch

```bash
gh repo view --json defaultBranchRef -q '.defaultBranchRef.name'
```

Use repo's default branch (usually `main` or `master`).

### 3. Create branch

```bash
git fetch origin
git checkout <target-branch>
git pull origin <target-branch>
git checkout -b <branch-name>
```

**Auto-generate branch name** (if not provided):
- `feat/<description>` — New features
- `fix/<description>` — Bug fixes
- `docs/<description>` — Documentation
- `refactor/<description>` — Refactoring
- `chore/<description>` — Maintenance

### 4. Stage and commit

```bash
git add -A
git diff --cached --name-only
```

Verify no sensitive files. Generate commit message:
- Format: `<type>: <short description>`
- Imperative mood, under 50 chars, no period

```bash
git commit -m "<message>"
```

### 5. Push and create PR

```bash
git push -u --follow-tags origin <branch-name>
gh pr create --base <target> --head <branch> --title "<title>" --body "<body>"
```

`--follow-tags` ensures any annotated tags created by hooks (e.g., harness version bump) are pushed with the branch.

**PR body format**:
```markdown
## Summary
<2-3 bullet points>

## Changes
- <file1>: <what changed>

## Test
- [ ] <suggested test>
```

### 6. Output

Show:
- Branch created: `<branch-name>`
- Commit: `<hash> <message>`
- PR created: `<PR-URL>`

## Error Handling

| Condition | Action |
|-----------|--------|
| No changes | Report and exit |
| Sensitive file detected | List files, abort |
| Branch exists | Suggest alternative or reuse |
| PR already exists | Show existing PR URL, abort |
| Push rejected | Suggest fetch + rebase |
| gh not authenticated | Suggest `gh auth login` |
