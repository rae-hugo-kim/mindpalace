#!/usr/bin/env node
// review-gate.mjs - PreToolUse hook for Bash (git commit)
// Purpose: Enforce review based on change risk level
// - critical/high risk + no review → BLOCK
// - critical/high risk + FAIL review → BLOCK
// - medium risk + no review → WARNING (recommend reviewer)
// - low risk → PASS (docs/config don't need adversarial review)
// Exit 0 = allow, Exit 2 = block

import { readFileSync, existsSync, appendFileSync, mkdirSync, readdirSync, unlinkSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';
import { assessRisk } from './risk-assess.mjs';

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
  appendFileSync(logFile, `[${timestamp}] review-gate: ${msg}\n`);
}

log('Hook started');

const command = data?.tool_input?.command || '';

if (!/(?:^|&&|\|\||;)\s*git\b[^|;]*\bcommit\b/.test(command)) {
  log('Not a git commit, allowing');
  process.exit(0);
}

const risk = assessRisk(cwd);
log(`Risk: ${risk.level} (${risk.reason}), ${risk.files.length} files, ~${risk.diffSize} lines`);

if (risk.level === 'low' || risk.level === 'none') {
  log('Low/no risk, review not required');
  process.exit(0);
}

const reviewDir = join(cwd, 'docs', 'reviews');
const skipFile = join(cwd, 'docs', 'harness', 'review-skip');

if (existsSync(skipFile)) {
  log('review-skip flag found, allowing');
  unlinkSync(skipFile);
  process.exit(0);
}

const today = new Date().toISOString().slice(0, 10);
let todayReviews = [];

if (existsSync(reviewDir)) {
  todayReviews = readdirSync(reviewDir).filter(f => f.startsWith(`review-${today}`));
}

if (todayReviews.length === 0) {
  if (risk.level === 'critical' || risk.level === 'high') {
    log(`BLOCKED: ${risk.level} risk with no review`);
    console.error(`HARNESS BLOCK: ${risk.level} risk changes (${risk.reason}) require review.`);
    console.error('Run reviewer agent first, or create docs/harness/review-skip to override.');
    process.exit(2);
  }
  log(`WARNING: ${risk.level} risk with no review`);
  console.error(`HARNESS WARNING: ${risk.level} risk changes without review. Consider running reviewer agent.`);
  process.exit(0);
}

const latestReview = join(reviewDir, todayReviews.sort().pop());
const content = readFileSync(latestReview, 'utf-8');

if (/Verdict:\s*FAIL/i.test(content)) {
  log('BLOCKED: Latest review verdict is FAIL');
  console.error(`HARNESS BLOCK: Latest review verdict is FAIL. Fix issues before committing.`);
  process.exit(2);
}

// Diff hash correlation check
let currentHash;
try {
  const staged = execSync('git diff --cached', { cwd, encoding: 'utf-8' });
  if (staged.trim()) {
    currentHash = execSync('git diff --cached | shasum -a 256', { cwd, encoding: 'utf-8', shell: true }).trim().split(' ')[0];
  } else {
    currentHash = execSync('git diff | shasum -a 256', { cwd, encoding: 'utf-8', shell: true }).trim().split(' ')[0];
  }
} catch { currentHash = null; }

if (currentHash && !content.includes('diff-hash: ' + currentHash)) {
  if (risk.level === 'critical' || risk.level === 'high') {
    log('BLOCKED: Review does not match current diff');
    console.error('HARNESS BLOCK: Review does not match current changes. Re-run reviewer agent.');
    process.exit(2);
  }
  log('WARNING: Review may not match current diff');
  console.error('HARNESS WARNING: Review may not cover current changes. Consider re-running reviewer.');
}

log(`Review exists (${todayReviews.length} today), verdict not FAIL, allowing`);
process.exit(0);
