#!/usr/bin/env node
// backpressure-gate.mjs - PreToolUse hook for Bash (git commit)
// Purpose: Block commits if build/test/lint not verified
// Risk-aware: docs-only changes skip test requirement
// Exit 0 = allow, Exit 2 = block

import { readFileSync, existsSync, appendFileSync, mkdirSync, unlinkSync } from 'fs';
import { join } from 'path';
import { assessRisk } from './risk-assess.mjs';

const input = readFileSync(0, 'utf-8');

let data;
try {
  data = JSON.parse(input);
} catch (e) {
  console.error('HARNESS WARNING: Hook received invalid input, skipping check.');
  process.exit(0);
}

const cwd = data?.session_state?.cwd || process.cwd();
const stateDir = join(cwd, '.omc', 'harness-state');
if (!existsSync(stateDir)) mkdirSync(stateDir, { recursive: true });

const logFile = join(stateDir, 'hook-debug.log');

function log(msg) {
  const timestamp = new Date().toISOString();
  appendFileSync(logFile, `[${timestamp}] backpressure-gate: ${msg}\n`);
}

log('Hook started');

const command = data?.tool_input?.command || '';
log(`Command: ${command}`);

if (!command.match(/(?:^|&&|\|\||;)\s*git\b[^|;]*\bcommit\b/)) {
  log('Not a git commit, allowing');
  process.exit(0);
}

log('Git commit detected, checking backpressure status');

const risk = assessRisk(cwd);
log(`Risk: ${risk.level} (${risk.reason})`);

if (risk.level === 'low' || risk.level === 'none') {
  log('Low/no risk (docs/config only), skipping test requirement');
  process.exit(0);
}

const skipFile = join(cwd, 'docs', 'harness', 'backpressure-skip');
if (existsSync(skipFile)) {
  log('backpressure-skip flag found, allowing');
  unlinkSync(skipFile);
  process.exit(0);
}

const statusFile = join(stateDir, 'backpressure-status');

if (!existsSync(statusFile)) {
  if (risk.level === 'critical' || risk.level === 'high') {
    log('No status file + high risk, blocking');
    console.error('HARNESS BLOCK: No build/test verification for high-risk changes.');
    console.error('Run tests first, or create docs/harness/backpressure-skip to override.');
    process.exit(2);
  }
  log('No status file + medium risk, warning');
  console.error('HARNESS WARNING: No build/test verification recorded. Consider running tests.');
  process.exit(0);
}

const status = readFileSync(statusFile, 'utf-8').trim();
log(`Status: ${status}`);

if (status === 'PASS') {
  log('Status is PASS, allowing');
  process.exit(0);
}

if (status === 'UNKNOWN') {
  log('Status is UNKNOWN, blocking');
  console.error('HARNESS BLOCK: No build/test verification in this session.');
  console.error('Run build/test/lint and ensure they pass before committing.');
  process.exit(2);
}

const failFile = join(stateDir, 'backpressure-last-fail');
const lastFail = existsSync(failFile) ? readFileSync(failFile, 'utf-8').trim() : 'unknown';
log(`Status is not PASS, blocking. Last fail: ${lastFail}`);
console.error(`HARNESS BLOCK: Last verification failed: ${lastFail}`);
console.error('Run build/test/lint and ensure they pass before committing.');
process.exit(2);
