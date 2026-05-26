#!/usr/bin/env node
// backpressure-tracker.mjs - PostToolUse hook for Bash
// Purpose: Track build/test/lint results (for backpressure-gate)

import { readFileSync, writeFileSync, mkdirSync, existsSync, unlinkSync, appendFileSync } from 'fs';
import { join } from 'path';

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
const historyFile = join(stateDir, 'test-history.json');

function log(msg) {
  const timestamp = new Date().toISOString();
  appendFileSync(logFile, `[${timestamp}] backpressure-tracker: ${msg}\n`);
}

log('Hook started');

const command = data?.tool_input?.command || '';
log(`Command: ${command}`);

// Patterns for build/test/lint commands
const buildPatterns = /npm run build|pnpm build|yarn build|tsc(?:\s|$)|make(?:\s|$)|cargo build|go build|mvn compile|gradle build/;
const testPatterns = /npm test|pnpm test|yarn test|pytest|jest|vitest|cargo test|go test|mvn test|gradle test/;
const lintPatterns = /npm run lint|pnpm lint|eslint|prettier|tsc --noEmit|cargo clippy|golangci-lint/;

let isVerification = false;
let verificationType = '';

if (buildPatterns.test(command)) {
  isVerification = true;
  verificationType = 'build';
} else if (testPatterns.test(command)) {
  isVerification = true;
  verificationType = 'test';
} else if (lintPatterns.test(command)) {
  isVerification = true;
  verificationType = 'lint';
}

log(`Is verification: ${isVerification}, type: ${verificationType}`);

if (isVerification) {
  const statusFile = join(stateDir, 'backpressure-status');
  const now = new Date();
  const timeStr = now.toTimeString().substring(0, 5);

  let history = { runs: [] };
  if (existsSync(historyFile)) {
    try {
      history = JSON.parse(readFileSync(historyFile, 'utf-8'));
    } catch {
      history = { runs: [] };
    }
  }

  // PostToolUse only fires on success, so this is always PASS
  const run = {
    time: timeStr,
    type: verificationType,
    cmd: command.length > 50 ? command.substring(0, 50) + '...' : command,
    result: 'PASS'
  };

  history.runs.push(run);
  history.lastResult = 'PASS';
  history.lastTime = now.toISOString();

  writeFileSync(historyFile, JSON.stringify(history, null, 2));
  writeFileSync(statusFile, 'PASS');
  try { unlinkSync(join(stateDir, 'backpressure-last-fail')); } catch {}

  log(`Added to history: ${JSON.stringify(run)}`);
}

process.exit(0);
