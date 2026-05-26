#!/usr/bin/env node
// acceptance-gate.mjs - PreToolUse hook for Bash(git commit*)
// Purpose: Block commits if acceptance criteria not met
// Logic: Pass if (all checkboxes checked) OR (acceptance-done flag exists)
// Exit 0 = allow, Exit 2 = block (uses stderr for messages)

import { readFileSync, existsSync, appendFileSync, mkdirSync } from 'fs';
import { join } from 'path';

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
  appendFileSync(logFile, `[${timestamp}] acceptance-gate: ${msg}\n`);
}

log('Hook started');

const command = data?.tool_input?.command || '';
log(`Command: ${command}`);

// Only check for git commit commands
if (!command.match(/(?:^|&&|\|\||;)\s*git\b[^|;]*\bcommit\b/)) {
  log('Not a git commit, allowing');
  process.exit(0);
}

log('Git commit detected, checking acceptance criteria');
log(`CWD: ${cwd}`);

// Support test mode with custom paths
const isTestMode = process.env.ACCEPTANCE_GATE_TEST === 'true';
const scopeFilePath = isTestMode
  ? process.env.TEST_SCOPE_FILE
  : join(cwd, 'docs', 'harness', 'current-scope.md');
const flagFilePath = isTestMode
  ? process.env.TEST_FLAG_FILE
  : join(cwd, 'docs', 'harness', 'acceptance-done');
const seedPath = isTestMode
  ? process.env.TEST_SEED_FILE
  : join(cwd, 'docs', 'harness', 'seed.yaml');

// Check 1: Flag file exists (manual override)
if (existsSync(flagFilePath)) {
  log('acceptance-done flag exists, allowing (manual override)');
  process.exit(0);
}

// Check 2: seed.yaml AC existence check
if (existsSync(seedPath)) {
  const seedContent = readFileSync(seedPath, 'utf-8');
  const hasAC = /^acceptance_criteria:\s*\n\s+-/m.test(seedContent);
  if (hasAC) {
    log('AC found in seed.yaml, checking completion via flag or scope file checkboxes');
  } else {
    log('seed.yaml exists but no AC defined, allowing with warning');
    console.error('HARNESS WARNING: seed.yaml has no acceptance_criteria. Run /kickoff to define them.');
    process.exit(0);
  }
}

// Check 3: Scope file exists (checkbox-based completion tracking)
if (!existsSync(scopeFilePath)) {
  if (existsSync(seedPath)) {
    log('seed.yaml has AC but no current-scope.md for checkbox tracking, allowing with warning');
    console.error('HARNESS WARNING: AC defined in seed.yaml but no current-scope.md for completion tracking.');
    process.exit(0);
  }
  log('No current-scope.md found, allowing with warning');
  console.error('HARNESS WARNING: No scope file. Run /kickoff to define acceptance criteria.');
  process.exit(0);
}

// Read scope file
const scopeContent = readFileSync(scopeFilePath, 'utf-8');

// Extract Acceptance Criteria section
const acceptanceMatch = scopeContent.match(/## Acceptance Criteria\s*\n([\s\S]*?)(?=\n##|\n*$)/i);
if (!acceptanceMatch) {
  log('No Acceptance Criteria section found, allowing with warning');
  console.error('HARNESS WARNING: No Acceptance Criteria section in scope file.');
  process.exit(0);
}

const acceptanceSection = acceptanceMatch[1];

// Find all checkboxes
const checkboxes = acceptanceSection.match(/- \[[ x]\]/g) || [];
const checked = acceptanceSection.match(/- \[x\]/gi) || [];
const unchecked = acceptanceSection.match(/- \[ \]/g) || [];

log(`Checkboxes: total=${checkboxes.length}, checked=${checked.length}, unchecked=${unchecked.length}`);

if (checkboxes.length === 0) {
  log('No checkboxes defined, allowing');
  process.exit(0);
}

if (unchecked.length === 0) {
  log('All acceptance criteria met, allowing');
  process.exit(0);
}

// Unchecked items exist and no flag file = block
log(`BLOCKED: ${unchecked.length} unchecked criteria, no override flag`);

const uncheckedItems = [];
const lines = acceptanceSection.split('\n');
for (const line of lines) {
  if (line.match(/- \[ \]/)) {
    uncheckedItems.push(line.replace(/- \[ \]/, '').trim());
  }
}

console.error(`HARNESS BLOCK: Cannot commit. ${unchecked.length} acceptance criteria not met:`);
uncheckedItems.slice(0, 3).forEach(item => console.error(`  - [ ] ${item}`));
if (uncheckedItems.length > 3) {
  console.error(`  ... and ${uncheckedItems.length - 3} more`);
}
console.error('');
console.error('Options:');
console.error('  1. Check off completed criteria in docs/harness/current-scope.md');
console.error('  2. Create docs/harness/acceptance-done to override');

process.exit(2);
