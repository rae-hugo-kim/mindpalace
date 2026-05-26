#!/usr/bin/env node
// harness-version-check.mjs - SessionStart hook
// Purpose: Notify when local harness is behind the source remote.
//
// Skip logic: if harness-meta.json has no `source_remote`, this IS the source
// repo. Consumer projects get `source_remote` + `commit_sha` written by the
// bootstrap skill.
//
// Version compare: primary = tag name (harness/YYYY.N), fallback = commit SHA.
// Cache: 24h in .omc/state/harness-version-check.json.

import { readFileSync, writeFileSync, existsSync, mkdirSync, statSync, renameSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { execFileSync } from 'node:child_process';
import process from 'node:process';

const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

let stdin = '';
try { stdin = readFileSync(0, 'utf-8'); } catch { /* no stdin is fine */ }
let data = {};
try { data = JSON.parse(stdin); } catch { /* ignore */ }

const force = process.argv.includes('--force');
const cwd = data?.session_state?.cwd || process.cwd();

// Log rotation: rotate hook-debug.log if it exceeds 1MB
const debugLogPath = join(cwd, '.omc', 'harness-state', 'hook-debug.log');
try {
  if (existsSync(debugLogPath) && statSync(debugLogPath).size > 1048576) {
    renameSync(debugLogPath, debugLogPath + '.old');
  }
} catch { /* ignore rotation errors */ }

const metaPath = join(cwd, '.claude/hooks/harness/harness-meta.json');
if (!existsSync(metaPath)) process.exit(0);

let meta;
try { meta = JSON.parse(readFileSync(metaPath, 'utf-8')); } catch { process.exit(0); }

const sourceRemote = meta.source_remote;
if (!sourceRemote) process.exit(0);

const cachePath = join(cwd, '.omc/state/harness-version-check.json');
const now = Date.now();

if (!force && existsSync(cachePath)) {
  try {
    const cached = JSON.parse(readFileSync(cachePath, 'utf-8'));
    if (cached.checkedAt && (now - cached.checkedAt) < CACHE_TTL_MS) {
      emitIfDrift(meta, cached);
      process.exit(0);
    }
  } catch { /* stale/corrupt cache — refetch */ }
}

let remote;
try {
  const output = execFileSync(
    'git',
    ['ls-remote', '--tags', sourceRemote, 'refs/tags/harness/*'],
    { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 10000 },
  );
  remote = parseRemoteTags(output);
} catch {
  process.exit(0);
}

if (!remote?.remoteLatestVersion) process.exit(0);

try {
  mkdirSync(dirname(cachePath), { recursive: true });
  writeFileSync(cachePath, JSON.stringify({
    checkedAt: now,
    remoteLatestVersion: remote.remoteLatestVersion,
    remoteLatestSha: remote.remoteLatestSha,
    source: sourceRemote,
  }, null, 2));
} catch { /* ignore cache write failure */ }

emitIfDrift(meta, remote);
process.exit(0);

function parseRemoteTags(output) {
  const re = /^([0-9a-f]{40})\s+refs\/tags\/harness\/(\d{4})\.(\d+)(?:\^\{\})?$/gm;
  let best = null;
  let m;
  while ((m = re.exec(output)) !== null) {
    const [, sha, yr, seq] = m;
    const rank = (+yr) * 1e6 + (+seq);
    if (!best || rank > best.rank) best = { rank, version: `${yr}.${seq}`, sha };
  }
  return best ? { remoteLatestVersion: best.version, remoteLatestSha: best.sha } : null;
}

function versionRank(v) {
  const m = /^(\d{4})\.(\d+)$/.exec(v || '');
  return m ? (+m[1]) * 1e6 + (+m[2]) : -1;
}

function emitIfDrift(localMeta, remoteInfo) {
  const lv = localMeta.version;
  const rv = remoteInfo.remoteLatestVersion;
  const lsha = localMeta.commit_sha;
  const rsha = remoteInfo.remoteLatestSha;

  const primaryDrift = versionRank(rv) > versionRank(lv);
  const fallbackDrift = !primaryDrift && lsha && rsha && lsha !== rsha;

  if (primaryDrift) {
    console.log(`HARNESS VERSION: local ${lv} → remote ${rv}. Run /harness-check for details or re-bootstrap to sync.`);
  } else if (fallbackDrift) {
    console.log(`HARNESS DRIFT: version matches (${lv}) but commit SHA differs. Run /harness-check for details.`);
  }
}
