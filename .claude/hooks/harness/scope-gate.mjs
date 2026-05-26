#!/usr/bin/env node
// scope-gate.mjs - PreToolUse hook for Edit|Write
// Purpose: Block edits to paths defined in OUT OF SCOPE
// Exit 0 = allow, Exit 2 = block (uses stderr for messages)

import { readFileSync, existsSync, appendFileSync, mkdirSync } from 'fs';
import { join, resolve } from 'path';

// Use project-local state directory
function getStateDir(cwd) {
  const dir = join(cwd, '.omc', 'harness-state');
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}

const input = readFileSync(0, 'utf-8');

let data;
try {
  data = JSON.parse(input);
} catch (e) {
  console.error('HARNESS WARNING: Hook received invalid input, skipping check.');
  process.exit(0);
}

const cwd = data?.session_state?.cwd || process.cwd();
const stateDir = getStateDir(cwd);
const logFile = join(stateDir, 'hook-debug.log');

function log(msg) {
  const timestamp = new Date().toISOString();
  appendFileSync(logFile, `[${timestamp}] scope-gate: ${msg}\n`);
}

log('Hook started');

const filePath = data?.tool_input?.file_path || data?.tool_input?.filePath;
log(`File path: ${filePath}`);

if (!filePath) {
  log('No file path, allowing');
  process.exit(0);
}

log(`CWD: ${cwd}`);

// Look for seed.yaml (primary) and current-scope.md (fallback)
const seedPath = join(cwd, 'docs', 'harness', 'seed.yaml');
const scopeFilePath = join(cwd, 'docs', 'harness', 'current-scope.md');

let outOfScopeItems = [];

if (existsSync(seedPath)) {
  const seedContent = readFileSync(seedPath, 'utf-8');
  const match = seedContent.match(/^out_of_scope:\s*\n((?:\s+-\s+.*\n?)*)/m);
  if (match) {
    outOfScopeItems = match[1].split('\n')
      .filter(l => l.trim().startsWith('-'))
      .map(l => l.replace(/^\s*-\s*/, '').trim())
      .filter(Boolean);
  }
  log(`Loaded ${outOfScopeItems.length} items from seed.yaml`);
} else if (existsSync(scopeFilePath)) {
  const scopeContent = readFileSync(scopeFilePath, 'utf-8');
  const outOfScopeMatch = scopeContent.match(/## OUT OF SCOPE\s*\n([\s\S]*?)(?=\n##|\n*$)/i);
  if (outOfScopeMatch) {
    outOfScopeItems = outOfScopeMatch[1]
      .split('\n')
      .filter(line => line.trim().startsWith('-'))
      .map(line => line.replace(/^-\s*/, '').trim())
      .filter(Boolean);
  }
  log(`Loaded ${outOfScopeItems.length} items from current-scope.md (fallback)`);
} else {
  log('No seed.yaml or current-scope.md found, allowing with warning');
  console.error('HARNESS WARNING: No scope file found. Run /kickoff to define scope.');
  process.exit(0);
}

log(`OUT OF SCOPE items: ${JSON.stringify(outOfScopeItems)}`);

if (outOfScopeItems.length === 0) {
  log('No OUT OF SCOPE items defined, allowing');
  process.exit(0);
}

function normalizePath(p) {
  return p.replace(/^[A-Za-z]:/, '').replace(/\\/g, '/').toLowerCase();
}

const normalizedFilePath = normalizePath(filePath);
const absoluteFilePath = normalizePath(resolve(cwd, filePath));

for (const item of outOfScopeItems) {
  const normalizedItem = normalizePath(item);
  if (normalizedFilePath.includes(normalizedItem) ||
      absoluteFilePath.includes(normalizedItem) ||
      normalizedItem.includes(normalizedFilePath)) {
    log(`BLOCKED: Path matches OUT OF SCOPE item: ${item}`);
    console.error(`HARNESS BLOCK: '${filePath}' is OUT OF SCOPE. Defined in scope: "${item}"`);
    process.exit(2);
  }
}

log('Path not in OUT OF SCOPE, allowing');
process.exit(0);
