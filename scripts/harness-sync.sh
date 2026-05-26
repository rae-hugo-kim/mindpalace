#!/usr/bin/env bash
# harness-sync.sh [--dry-run]
# Overwrites local harness files from the source remote's latest harness/* tag.
# Used by /harness-check to retrofit unregistered projects or sync drifted ones.
# Policy: remote wins unconditionally. Local tuning is not preserved.

set -euo pipefail

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

REPO_ROOT="$(git rev-parse --show-toplevel)"
META_FILE="$REPO_ROOT/.claude/hooks/harness/harness-meta.json"
DEFAULT_SOURCE="git@github.com:rae-hugo-kim/claude.git"
SOURCE_MATCH_RE="rae-hugo-kim/claude(\.git)?$"

# --- 1. Detect source repo (self-skip) ---
origin_url=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)
if [[ "$origin_url" =~ $SOURCE_MATCH_RE ]]; then
  echo "This IS the source harness repo. Nothing to sync."
  exit 0
fi

# --- 2. Resolve source_remote (fallback to default if unregistered) ---
source_remote=""
if [[ -f "$META_FILE" ]]; then
  source_remote=$(grep -o '"source_remote"[[:space:]]*:[[:space:]]*"[^"]*"' "$META_FILE" \
    | sed 's/.*"source_remote"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || true)
fi
if [[ -z "$source_remote" ]]; then
  echo "No source_remote in meta. Treating as unregistered — using default: $DEFAULT_SOURCE"
  source_remote="$DEFAULT_SOURCE"
fi
echo "Source: $source_remote"

# --- 3. Find latest harness/* tag on remote ---
latest_tag=$(git ls-remote --tags "$source_remote" 'refs/tags/harness/*' 2>/dev/null \
  | awk '{ print $2 }' \
  | sed 's|refs/tags/harness/||; s|\^{}$||' \
  | sort -u -t. -k1,1n -k2,2n \
  | tail -1)

if [[ -z "$latest_tag" ]]; then
  echo "Error: no harness/* tags on $source_remote" >&2
  exit 1
fi
echo "Target: harness/$latest_tag"

# --- 4. Shallow clone the target tag into temp ---
tmp=$(mktemp -d)
trap "rm -rf $tmp" EXIT
git clone --quiet --depth 1 --branch "harness/$latest_tag" "$source_remote" "$tmp"
target_sha=$(git -C "$tmp" rev-parse HEAD)

# --- 5. Paths to overwrite (harness assets only — never user code) ---
PATHS=(
  "rules"
  "checklists"
  "templates"
  "CLAUDE.md"
  ".claude/hooks/harness"
  ".claude/settings.json"
  ".githooks/post-commit"
  "scripts/harness-version-bump.sh"
  "scripts/harness-sync.sh"
  ".claude/skills/bootstrap"
  ".claude/skills/init"
  ".claude/skills/kickoff"
  ".claude/skills/startdev"
  ".claude/skills/sum"
  ".claude/skills/compr"
  ".claude/skills/compush"
  ".claude/skills/tidy"
  ".claude/skills/harness-check"
  ".claude/skills/code-review"
  ".claude/skills/receiving-code-review"
)

if [[ $DRY_RUN -eq 1 ]]; then
  echo "--- Dry run: paths that would be overwritten ---"
  for p in "${PATHS[@]}"; do
    if [[ -e "$tmp/$p" ]]; then
      echo "  WRITE  $p"
    else
      echo "  SKIP   $p (not in source)"
    fi
  done
  exit 0
fi

# --- 6. Copy (remote wins) ---
for p in "${PATHS[@]}"; do
  [[ -e "$tmp/$p" ]] || continue
  mkdir -p "$(dirname "$REPO_ROOT/$p")"
  if [[ -d "$tmp/$p" ]]; then
    rm -rf "$REPO_ROOT/$p"
    cp -r "$tmp/$p" "$REPO_ROOT/$p"
  else
    cp "$tmp/$p" "$REPO_ROOT/$p"
  fi
done

# --- 7. Rewrite harness-meta.json (preserve bootstrapped_at) ---
bootstrapped_at=""
if [[ -f "$META_FILE" ]]; then
  bootstrapped_at=$(grep -o '"bootstrapped_at"[[:space:]]*:[[:space:]]*"[^"]*"' "$META_FILE" \
    | sed 's/.*"bootstrapped_at"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || true)
fi
[[ -z "$bootstrapped_at" ]] && bootstrapped_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

src_desc=$(grep -o '"description"[[:space:]]*:[[:space:]]*"[^"]*"' "$tmp/.claude/hooks/harness/harness-meta.json" \
  | sed 's/.*"description"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || echo "")
today=$(date +%Y-%m-%d)

cat > "$META_FILE" <<EOF
{
  "version": "$latest_tag",
  "updated": "$today",
  "description": "$src_desc",
  "source_remote": "$source_remote",
  "commit_sha": "$target_sha",
  "bootstrapped_at": "$bootstrapped_at"
}
EOF

# --- 8. Clear stale check cache ---
cache="$REPO_ROOT/.omc/state/harness-version-check.json"
[[ -f "$cache" ]] && rm -f "$cache"

echo "Synced to harness/$latest_tag (SHA: ${target_sha:0:7})"
