# Hook Recipes

<!-- Inspired by ECC hooks system. Complements harness_integration_contract.md (verification hooks) with creation guidance and ready-to-use recipes. -->

## Purpose

Concrete, ready-to-use Claude Code hook recipes for enforcing code quality automatically. Adapt commands to your project's actual toolchain (see `repo_command_discovery.md`).

---

## Hook Types

| Type | When | Can Block? | Use For |
|------|------|------------|---------|
| `PreToolUse` | Before tool executes | Yes (exit 2) | Prevent dangerous operations |
| `PostToolUse` | After tool completes | No | Analyze output, auto-format, warn |
| `Stop` | After each Claude response | No | Session state, pattern extraction |
| `SessionStart` | Session begins | No | Load context, detect environment |
| `PreCompact` | Before context compaction | No | Save state before memory loss |

**Exit codes**: `0` = pass, `2` = block (PreToolUse only), other non-zero = error (logged, not blocking).

**Input schema** (JSON on stdin):

```json
{
  "tool_name": "Edit|Write|Bash|Read|...",
  "tool_input": {
    "command": "...",
    "file_path": "...",
    "content": "...",
    "old_string": "...",
    "new_string": "..."
  },
  "tool_output": { "output": "..." }
}
```

`tool_output` is only available in `PostToolUse` hooks.

---

## Recipe 1: Block large file creation (PreToolUse)

Prevents creating files over 800 lines. Enforces the file size limit from `coding_standards.md`.

```json
{
  "matcher": "Write",
  "hooks": [{
    "type": "command",
    "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const c=i.tool_input?.content||'';const lines=c.split('\\n').length;if(lines>800){console.error('[Hook] BLOCKED: File exceeds 800 lines ('+lines+')');console.error('[Hook] Split into smaller, focused modules');process.exit(2)}console.log(d)})\""
  }],
  "description": "Block creation of files larger than 800 lines"
}
```

## Recipe 2: Warn on TODO/FIXME additions (PostToolUse)

Non-blocking warning when new TODO/FIXME comments are added.

```json
{
  "matcher": "Edit",
  "hooks": [{
    "type": "command",
    "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const ns=i.tool_input?.new_string||'';if(/TODO|FIXME|HACK/.test(ns)){console.error('[Hook] New TODO/FIXME added - consider creating an issue')}console.log(d)})\""
  }],
  "description": "Warn when adding TODO/FIXME comments"
}
```

## Recipe 3: Test file reminder for new source files (PostToolUse)

Reminds to create tests when adding new source files without a corresponding test file.

```json
{
  "matcher": "Write",
  "hooks": [{
    "type": "command",
    "command": "node -e \"const fs=require('fs');let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const p=i.tool_input?.file_path||'';if(/src\\/.*\\.(ts|js|py)$/.test(p)&&!/\\.test\\.|\\.spec\\./.test(p)){const ext=p.match(/\\.(ts|js|py)$/)[0];const testPath=p.replace(new RegExp(ext+'$'),'.test'+ext);if(!fs.existsSync(testPath)){console.error('[Hook] No test file for: '+p);console.error('[Hook] Expected: '+testPath)}}console.log(d)})\""
  }],
  "description": "Remind to create tests for new source files"
}
```

## Recipe 4: Auto-format after edits (PostToolUse)

Template — replace the formatter command with your project's tool.

```json
{
  "matcher": "Edit",
  "hooks": [{
    "type": "command",
    "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const p=i.tool_input?.file_path||'';if(/\\.(ts|tsx|js|jsx)$/.test(p)){try{require('child_process').execFileSync('npx',['prettier','--write',p],{stdio:'pipe'})}catch(e){}}console.log(d)})\""
  }],
  "description": "Auto-format JS/TS files after edits (adapt command to your formatter)"
}
```

## Recipe 5: Block dev server outside tmux (PreToolUse)

Prevents running dev servers directly — they should run in tmux for log access.

```json
{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const i=JSON.parse(d);const cmd=i.tool_input?.command||'';if(/npm run dev|yarn dev|pnpm dev|next dev/.test(cmd)&&!process.env.TMUX){console.error('[Hook] BLOCKED: Run dev servers inside tmux');console.error('[Hook] Use: tmux new-session -d -s dev \\\"npm run dev\\\"');process.exit(2)}console.log(d)})\""
  }],
  "description": "Block dev server commands outside tmux sessions"
}
```

---

---

## Writing Custom Hooks

1. Read JSON from stdin, parse it.
2. Inspect `tool_name` and `tool_input` fields.
3. Write warnings to stderr (always shown to the agent).
4. Exit with code 2 to block (PreToolUse only).
5. Always output the original JSON to stdout.

See `harness_integration_contract.md` for the project's existing verification hooks.
