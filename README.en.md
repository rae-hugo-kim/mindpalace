**[한국어](README.md)**

# claude — Claude Code Harness Template

A policy framework that makes Claude Code behave consistently and safely.

Clone this repo and you get rules, checklists, skills, and hooks as a single package.
Delete what you don't need. Adapt the rest to your project.

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- [oh-my-claudecode](https://github.com/yeachan-heo/oh-my-claudecode) (OMC)

Without OMC, core features like agent delegation and hook automation won't work.

## Getting Started

### 1. Set Up Environment (once per machine)

```bash
/bootstrap
```

Installs OMC, RTK, and general-purpose MCP servers (context7, serena, exa, browser-tools).
Optionally add supabase, react-design-systems, and more.

### 2. Create a Project

```bash
/init my-project          # public
/init my-project --private # private
```

Creates a new GitHub repository based on this template.

### 3. Start Building

```
/kickoff    →  Define scope (goals, constraints, acceptance criteria)
/startdev   →  TDD-driven implementation
/compr      →  Create a pull request
```

## Structure

```
.
├── CLAUDE.md              Agent policy entry point
├── rules/                 Behavior rules
│   ├── safety_security    Safety & security
│   ├── anti_hallucination Evidence-based behavior
│   ├── change_control     Minimal change principle
│   ├── tdd_policy         RED → GREEN → TIDY
│   ├── ...                Each file has a one-line description
│   └── INDEX.md           Full listing
├── checklists/            Task checklists
├── templates/             Reusable templates
├── .claude/
│   ├── skills/            Skill definitions
│   │   ├── bootstrap/             Environment setup
│   │   ├── init/                  Project creation
│   │   ├── kickoff/               Scope interview
│   │   ├── startdev/              TDD implementation
│   │   ├── compr/                 PR creation
│   │   ├── compush/               Commit + push
│   │   ├── sum/                   Session summary
│   │   ├── tidy/                  Refactoring
│   │   ├── code-review/           Code review (3-pass)
│   │   ├── receiving-code-review/ Review intake guide
│   │   ├── harness-check/         Harness drift check + sync + audit
│   │   └── grepai-search/         Semantic code search
│   ├── hooks/harness/     Harness hooks
│   └── settings.json      Hook registration
├── docs/harness/          Harness runtime files
└── claudedocs/            Reference docs
```

## Skills

| Command | What it does |
|---------|-------------|
| `/bootstrap` | Set up dev environment (OMC + RTK + MCP servers) |
| `/init <name>` | Create new project from this template |
| `/kickoff` | Define goals, constraints, acceptance criteria |
| `/startdev` | Start TDD implementation from seed.yaml |
| `/sum` | Save session summary to `docs/sum/` |
| `/compr` | Branch → commit → push → PR |
| `/compush` | Commit → push (no PR) |
| `/tidy` | Refactor with Kent Beck's Tidy First |
| `/code-review` | 3-pass adversarial review of pending changes |
| `/receiving-code-review` | Verify and apply review feedback |
| `/harness-check` | Check harness drift and auto-sync from the source remote (`--audit` for 7-category quality score) |
| `/grepai-search` | Semantic code search for cold-start orientation |

## Harness

Automated guardrails that activate during the kickoff → startdev flow:

- **seed.yaml** — Structured kickoff output (goals, constraints, AC, risks)
- **scope-gate hook** — Blocks edits to out-of-scope paths
- **context-gate + read-tracker hooks** — Prevents editing unread files
- **acceptance-gate hook** — Blocks commits with unmet acceptance criteria
- **backpressure hooks** — Suppresses commits without verification (gate + tracker + invalidator)
- **kickoff-detector hook** — Reminds to kickoff when new work is detected
- **mcp-gate hook** — Enforces MCP server usage policy
- **destructive-guard hook** — Blocks dangerous commands (rm -rf, force push, etc.)
- **risk-assess hook** — Auto-assesses change impact
- **review-gate hook** — Forces review when risk threshold is crossed
- **harness-version-check hook** — Notifies of remote harness drift on SessionStart
- **rubric** — 4-dimension clarity gate (HIGH/MED/LOW)
- **audit log** — Event tracking (append-only JSONL)
- **glossary** — Project terminology alignment (`docs/glossary.yaml`)

## Harness Version Management

This repository serves as the **harness source** that other projects sync from.

### This repo (source) — automatic version bump

When `rules/`, `checklists/`, `.claude/`, `CLAUDE.md`, etc. change, `harness-meta.json` is bumped and a `harness/YYYY.N` tag is created. Activate the hook once after cloning:

```bash
git config core.hooksPath .githooks
```

After that, `git commit` automatically calls `scripts/harness-version-bump.sh`. Commits that touch only non-harness files are left alone.

### Other projects (consumer) — `/harness-check`

Projects created with `/init` or `/bootstrap` get a SessionStart hook that checks the remote harness tag every 24 hours and reports drift. To explicitly sync:

```bash
/harness-check              # overwrite-sync to the latest harness/* tag
/harness-check --dry-run    # preview the paths that would be overwritten
/harness-check --audit      # after sync, print 7-category (0–70) quality score
```

`--audit` invokes `scripts/harness-audit.sh` and scores tool_coverage, context_efficiency, quality_gates, memory_persistence, eval_coverage, security_guardrails, cost_efficiency.

## Customizing Rules

Each file under `rules/` is an independent rule.
Delete the ones you don't need — the rest keeps working.

| Category | Rules |
|----------|-------|
| **Safety** | safety_security, agent_security, anti_hallucination, repo_command_discovery |
| **Quality** | coding_standards, verification_tests_and_evals, change_control, tdd_policy, code_review_policy, quality_gates |
| **Tools** | mcp_policy, context7_policy, hook_recipes |
| **Process** | assetization, commit_and_pr, harness_integration_contract |
| **Docs** | documentation_policy |
| **Operations** | context_management, session_persistence, cost_awareness, learning_policy |

## Core Principles

1. **Think Before Coding** — State assumptions explicitly; ask when uncertain
2. **Simplicity First** — Build only what's requested; no over-engineering
3. **Surgical Changes** — Edit only relevant code; match existing style
4. **Goal-Driven Execution** — Turn vague requests into verifiable objectives

## License

See repository for license details.
