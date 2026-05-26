#!/usr/bin/env node
// destructive-guard.mjs - PreToolUse hook for Bash
// Purpose: Warn when dangerous shell commands are detected

import { readFileSync, existsSync, appendFileSync, mkdirSync } from 'fs';
import { join } from 'path';

function getStateDir(cwd) {
  const dir = join(cwd, '.omc', 'harness-state');
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}

const input = readFileSync(0, 'utf-8');

let data;
try {
  data = JSON.parse(input);
} catch {
  console.error('HARNESS WARNING: Hook received invalid input, skipping check.');
  process.exit(0);
}

const cwd = data?.session_state?.cwd || process.cwd();
const stateDir = getStateDir(cwd);
const logFile = join(stateDir, 'hook-debug.log');

function log(msg) {
  const timestamp = new Date().toISOString();
  appendFileSync(logFile, `[${timestamp}] destructive-guard: ${msg}\n`);
}

log('Hook started');

const command = data?.tool_input?.command || '';
log(`Command: ${command.slice(0, 120)}`);

// Code file extensions to detect overwrite-via-redirect
const CODE_EXTS = /\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|rb|php|sh|sql)$/;

const DESTRUCTIVE_PATTERNS = [
  { pattern: /rm\s+-[a-z]*r[a-z]*f|rm\s+-[a-z]*f[a-z]*r/, label: 'rm -rf' },
  { pattern: /rm\s+-r\b/, label: 'rm -r' },
  { pattern: /\brmdir\b/, label: 'rmdir' },
  { pattern: /git\s+checkout\s+--\s+\./, label: 'git checkout -- .' },
  { pattern: /git\s+checkout\s+\.$/, label: 'git checkout .' },
  { pattern: /git\s+clean\s+-[a-z]*f/, label: 'git clean -f' },
  { pattern: /git\s+reset\s+--hard/, label: 'git reset --hard' },
  { pattern: /sed\s+-i/, label: 'sed -i (in-place edit bypasses edit gates)' },
];

// Check for truncation via redirect on code files: "> some/file.ts"
const redirectMatch = command.match(/>\s*(['"]?)([^\s'";&|]+\.[a-z]+)\1/);
if (redirectMatch) {
  const targetFile = redirectMatch[2];
  if (CODE_EXTS.test(targetFile)) {
    DESTRUCTIVE_PATTERNS.push({ pattern: /./, label: `> ${targetFile} (truncation of code file)` });
  }
}

// Check for mv/cp overwriting code files
const mvCpMatch = command.match(/\b(?:mv|cp)\b[^|;&\n]*\s+(['"]?)([^\s'";&|]+\.[a-z]+)\1/);
if (mvCpMatch) {
  const targetFile = mvCpMatch[2];
  if (CODE_EXTS.test(targetFile)) {
    DESTRUCTIVE_PATTERNS.push({ pattern: /./, label: `mv/cp overwriting ${targetFile}` });
  }
}

const matched = DESTRUCTIVE_PATTERNS.find(({ pattern }) => pattern.test(command));

if (!matched) {
  log('No destructive pattern matched, allowing');
  process.exit(0);
}

log(`Destructive pattern matched: ${matched.label}`);
console.error(`HARNESS WARNING: Destructive command detected: ${matched.label}. Consider using Edit tool instead.`);

process.exit(0);
