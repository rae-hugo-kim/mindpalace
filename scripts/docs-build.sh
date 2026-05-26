#!/usr/bin/env bash
#
# scripts/docs-build.sh — Build docs site via mdBook + Mermaid validation.
#
# AC1 (docs/harness/seed.yaml) Mermaid validation ladder:
#   1) mdbook-mermaid preprocessor   — client-side render, no syntax check
#   2) mdbook-mermaid-mmdr           — SSR, validates (not installed by default)
#   3) mermaid-cli (mmdc)            — install: npm i -g @mermaid-js/mermaid-cli
#
# Build output: book/ (gitignored).
#
# Skip validation with --no-validate or NO_MERMAID_VALIDATE=1.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# cargo-installed tools (mdbook, mdbook-mermaid)
export PATH="$HOME/.cargo/bin:$PATH"

# Self-check: required tools (fresh-clone friendly)
missing=()
command -v mdbook >/dev/null 2>&1         || missing+=("mdbook (cargo install mdbook)")
command -v mdbook-mermaid >/dev/null 2>&1 || missing+=("mdbook-mermaid (cargo install mdbook-mermaid)")

if [ "${NO_MERMAID_VALIDATE:-0}" != "1" ] && [ "${1:-}" != "--no-validate" ]; then
  command -v mmdc >/dev/null 2>&1         || missing+=("mmdc (npm install -g @mermaid-js/mermaid-cli)")
fi

if [ ${#missing[@]} -gt 0 ]; then
  echo "[docs-build] ERROR: required tools not found:"
  for m in "${missing[@]}"; do echo "  - $m"; done
  echo
  echo "[docs-build] One-line install all:"
  echo "  cargo install mdbook mdbook-mermaid && npm install -g @mermaid-js/mermaid-cli"
  echo "[docs-build] Or run the harness bootstrap skill (handles tooling)."
  exit 1
fi

# Regenerate mermaid runtime assets if missing (gitignored as 2.6MB blob)
if [ ! -f "$ROOT/mermaid.min.js" ] || [ ! -f "$ROOT/mermaid-init.js" ]; then
  echo "[docs-build] Installing mermaid runtime assets..."
  mdbook-mermaid install "$ROOT" >/dev/null
fi

# 1. mdbook build (preprocessor renders mermaid blocks client-side)
mdbook build

# 2. Mermaid syntax validation
if [ "${NO_MERMAID_VALIDATE:-0}" = "1" ] || [ "${1:-}" = "--no-validate" ]; then
  echo "[docs-build] Mermaid validation skipped."
  echo "[docs-build] Done. Output: $ROOT/book/"
  exit 0
fi

if ! command -v mmdc >/dev/null 2>&1; then
  echo "[docs-build] ERROR: mmdc not found — Mermaid syntax validation required."
  echo "[docs-build]        Install: npm install -g @mermaid-js/mermaid-cli"
  echo "[docs-build]        Or skip: NO_MERMAID_VALIDATE=1 bash scripts/docs-build.sh"
  exit 1
fi

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# Extract mermaid blocks from docs/ and validate
python3 - "$tmpdir" <<'PY'
import re, sys, pathlib
tmpdir = pathlib.Path(sys.argv[1])
docs = pathlib.Path('docs')
n = 0
for md in docs.rglob('*.md'):
    text = md.read_text(encoding='utf-8', errors='ignore')
    for i, block in enumerate(re.findall(r'```mermaid\s*\n(.*?)\n```', text, re.DOTALL)):
        out = tmpdir / f'block-{n}.mmd'
        out.write_text(block, encoding='utf-8')
        # Stash source path next to the block for diagnostics
        (tmpdir / f'block-{n}.src').write_text(f'{md}:block#{i}', encoding='utf-8')
        n += 1
print(f'[docs-build] Extracted {n} mermaid block(s).')
PY

fail=0
shopt -s nullglob   # empty glob expands to nothing instead of literal
for mmd in "$tmpdir"/block-*.mmd; do
  src=$(cat "${mmd%.mmd}.src")
  if ! mmdc -i "$mmd" -o "$tmpdir/out.svg" --quiet >/dev/null 2>&1; then
    echo "[docs-build] FAIL: Mermaid syntax error in $src"
    echo "----"
    cat "$mmd"
    echo "----"
    fail=1
  fi
done

if [ "$fail" -eq 1 ]; then
  echo "[docs-build] Mermaid validation failed."
  exit 1
fi

echo "[docs-build] Mermaid OK."
echo "[docs-build] Done. Output: $ROOT/book/"
