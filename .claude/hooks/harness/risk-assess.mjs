#!/usr/bin/env node
// risk-assess.mjs - Shared risk assessment module for harness gates
// Not a hook itself — imported by other hooks.
// Usage: import { assessRisk } from './risk-assess.mjs';

import { execSync } from 'child_process';

const HIGH_RISK_PATTERNS = [
  /\.(env|pem|key|secret)$/i,
  /auth/i,
  /rls|policy|policies/i,
  /migration/i,
  /schema/i,
  /password|credential|token/i,
];

const CODE_EXTENSIONS = [
  '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
  '.py', '.go', '.rs', '.java', '.rb', '.php',
  '.sql', '.sh',
];

const DOCS_EXTENSIONS = ['.md', '.txt', '.mdx'];

const CONFIG_EXTENSIONS = ['.json', '.yaml', '.yml', '.toml', '.xml', '.ini'];

const CI_BUILD_PATTERNS = [
  /package\.json$/,
  /package-lock\.json$/,
  /yarn\.lock$/,
  /pnpm-lock\.yaml$/,
  /tsconfig.*\.json$/,
  /\.github\/workflows\//,
  /\.gitlab-ci\.yml$/,
  /Dockerfile/,
  /docker-compose/,
  /\.env\.example$/,
  /Makefile$/,
];

export function assessRisk(cwd) {
  let changedFiles;
  try {
    const staged = execSync('git diff --cached --name-only', { cwd, encoding: 'utf-8' }).trim();
    const unstaged = execSync('git diff --name-only', { cwd, encoding: 'utf-8' }).trim();
    changedFiles = [...new Set([...staged.split('\n'), ...unstaged.split('\n')])].filter(Boolean);
  } catch {
    return { level: 'unknown', reason: 'git diff failed', files: [] };
  }

  if (changedFiles.length === 0) {
    return { level: 'none', reason: 'no changes', files: [] };
  }

  const hasCIBuild = changedFiles.some(f =>
    CI_BUILD_PATTERNS.some(p => p.test(f))
  );

  const isDocsOnly = changedFiles.every(f =>
    DOCS_EXTENSIONS.some(ext => f.endsWith(ext)) || f.startsWith('docs/')
  );

  const isConfigOnly = changedFiles.every(f =>
    CONFIG_EXTENSIONS.some(ext => f.endsWith(ext)) ||
    DOCS_EXTENSIONS.some(ext => f.endsWith(ext))
  );

  const hasCode = changedFiles.some(f =>
    CODE_EXTENSIONS.some(ext => f.endsWith(ext))
  );

  const hasHighRisk = changedFiles.some(f =>
    HIGH_RISK_PATTERNS.some(p => p.test(f))
  );

  let diffSize = 0;
  try {
    const cachedStat = execSync('git diff --cached --shortstat', { cwd, encoding: 'utf-8' }).trim();
    const unstagedStat = execSync('git diff --shortstat', { cwd, encoding: 'utf-8' }).trim();
    for (const stat of [cachedStat, unstagedStat]) {
      const insertions = stat.match(/(\d+) insertion/);
      const deletions = stat.match(/(\d+) deletion/);
      if (insertions) diffSize += parseInt(insertions[1]);
      if (deletions) diffSize += parseInt(deletions[1]);
    }
  } catch { /* ignore */ }

  if (hasHighRisk) {
    return {
      level: 'critical',
      reason: 'security/auth/migration files changed',
      files: changedFiles,
      diffSize,
    };
  }

  if (hasCode && diffSize > 100) {
    return {
      level: 'high',
      reason: `${diffSize}+ lines of code changed`,
      files: changedFiles,
      diffSize,
    };
  }

  if (hasCode) {
    return {
      level: 'medium',
      reason: 'code changes detected',
      files: changedFiles,
      diffSize,
    };
  }

  if (isDocsOnly) {
    return {
      level: 'low',
      reason: 'documentation only',
      files: changedFiles,
      diffSize,
    };
  }

  if (isConfigOnly) {
    if (hasCIBuild) {
      return { level: 'medium', reason: 'CI/build config changed', files: changedFiles, diffSize };
    }
    return {
      level: 'low',
      reason: 'config/docs only',
      files: changedFiles,
      diffSize,
    };
  }

  return {
    level: 'medium',
    reason: 'mixed changes',
    files: changedFiles,
    diffSize,
  };
}
