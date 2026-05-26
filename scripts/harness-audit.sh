#!/usr/bin/env bash
# scripts/harness-audit.sh [--root PATH] [--terse]
#
# Deterministic 7-category quality audit of a harness layout.
# Each category scores 0..10 by checking file presence and content patterns.
# Total range: 0..70.
#
# Used by the harness-check skill to track quality over time.
# Output:
#   default — human-readable per-category breakdown + TOTAL line
#   --terse — TOTAL + one line per category, machine-parseable
#
# Categories (10 each):
#   tool_coverage          — agents, hooks, scripts, routing, model selection
#   context_efficiency     — context budget rules, session persistence, compaction
#   quality_gates          — review policy, verification, gate hooks
#   memory_persistence     — auto-memory, session state, summarization
#   eval_coverage          — eval templates, checklist, EDD content
#   security_guardrails    — security rules, destructive guard, mcp gate
#   cost_efficiency        — cost rules, model routing, token budget guidance

set -euo pipefail

ROOT="$(pwd)"
TERSE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      [[ $# -ge 2 ]] || { echo "Missing argument for --root" >&2; exit 2; }
      ROOT="$2"; shift 2;;
    --terse) TERSE=1; shift;;
    -h|--help)
      sed -n '2,18p' "$0" | sed 's/^# \?//'; exit 0;;
    *) echo "Unknown flag: $1" >&2; exit 2;;
  esac
done

[[ -d "$ROOT" ]] || { echo "Root not a directory: $ROOT" >&2; exit 2; }

# --- helpers (read-only, deterministic) ---

# Returns 0 if path exists relative to ROOT.
exists() { [[ -e "$ROOT/$1" ]]; }

# Returns 0 if file contains pattern (fixed string, no regex).
has_pattern() {
  local file="$1" pat="$2"
  [[ -f "$ROOT/$file" ]] && grep -qF -- "$pat" "$ROOT/$file"
}

# Counts regular files in a directory (0 if absent).
count_files() {
  local dir="$ROOT/$1"
  [[ -d "$dir" ]] || { echo 0; return; }
  find "$dir" -type f 2>/dev/null | wc -l | tr -d ' '
}

# Greps a pattern across a glob, returns 0 if any match.
grep_any() {
  local pattern="$1"; shift
  local f
  for f in "$@"; do
    [[ -f "$f" ]] && grep -qF -- "$pattern" "$f" && return 0
  done
  return 1
}

# --- per-category check tables ---
# Each function appends "+N name" lines to a shared array DETAIL_<cat>
# and writes the integer score into SCORE_<cat>.

declare -a DETAIL_tool_coverage DETAIL_context_efficiency DETAIL_quality_gates
declare -a DETAIL_memory_persistence DETAIL_eval_coverage DETAIL_security_guardrails
declare -a DETAIL_cost_efficiency

SCORE_tool_coverage=0
SCORE_context_efficiency=0
SCORE_quality_gates=0
SCORE_memory_persistence=0
SCORE_eval_coverage=0
SCORE_security_guardrails=0
SCORE_cost_efficiency=0

award() {
  local cat="$1" pts="$2" label="$3"
  local -n score_ref="SCORE_$cat"
  local -n detail_ref="DETAIL_$cat"
  score_ref=$(( score_ref + pts ))
  detail_ref+=("+$pts $label")
}

skip() {
  local cat="$1" label="$2"
  local -n detail_ref="DETAIL_$cat"
  detail_ref+=("+0 $label (missing)")
}

emit_category() {
  local cat="$1"
  local -n score_ref="SCORE_$cat"
  local -n detail_ref="DETAIL_$cat"
  echo "## ${cat//_/ } : ${score_ref}/10"
  local line
  for line in "${detail_ref[@]}"; do
    echo "  $line"
  done
  echo ""
}

# --- 1. Tool Coverage ---
score_tool_coverage() {
  local agents
  agents=$(count_files ".claude/agents")
  if (( agents >= 5 )); then
    award tool_coverage 3 ".claude/agents/ has $agents agents (>=5)"
  elif (( agents > 0 )); then
    award tool_coverage 1 ".claude/agents/ has $agents agents (<5)"
  else
    skip tool_coverage ".claude/agents/"
  fi

  if exists ".claude/hooks/harness"; then
    award tool_coverage 2 ".claude/hooks/harness/ present"
  else
    skip tool_coverage ".claude/hooks/harness/"
  fi

  if (( $(count_files "scripts") >= 3 )); then
    award tool_coverage 2 "scripts/ has 3+ files"
  elif exists "scripts"; then
    award tool_coverage 1 "scripts/ exists, <3 files"
  else
    skip tool_coverage "scripts/"
  fi

  if exists "rules/agent_routing.md"; then
    award tool_coverage 1 "rules/agent_routing.md"
  else
    skip tool_coverage "rules/agent_routing.md"
  fi

  if has_pattern "CLAUDE.md" "model_routing" || has_pattern "CLAUDE.md" "model routing"; then
    award tool_coverage 2 "CLAUDE.md model_routing block"
  else
    skip tool_coverage "CLAUDE.md model_routing block"
  fi
}

# --- 2. Context Efficiency ---
score_context_efficiency() {
  if exists "rules/context_management.md"; then
    award context_efficiency 3 "rules/context_management.md"
  else
    skip context_efficiency "rules/context_management.md"
  fi

  if exists "rules/session_persistence.md"; then
    award context_efficiency 2 "rules/session_persistence.md"
  else
    skip context_efficiency "rules/session_persistence.md"
  fi

  if grep -rqF ".omc/state" "$ROOT/CLAUDE.md" "$ROOT/rules" 2>/dev/null; then
    award context_efficiency 2 ".omc/state referenced in rules/CLAUDE.md"
  else
    skip context_efficiency ".omc/state reference"
  fi

  # PreCompact hook (Node or shell)
  if compgen -G "$ROOT/.claude/hooks/harness/pre-compact.*" >/dev/null 2>&1; then
    award context_efficiency 3 "PreCompact hook present"
  else
    skip context_efficiency "PreCompact hook (.claude/hooks/harness/pre-compact.*)"
  fi
}

# --- 3. Quality Gates ---
score_quality_gates() {
  if exists "rules/code_review_policy.md"; then
    award quality_gates 2 "rules/code_review_policy.md"
  else
    skip quality_gates "rules/code_review_policy.md"
  fi

  if exists "checklists/code_review.md"; then
    award quality_gates 1 "checklists/code_review.md"
  else
    skip quality_gates "checklists/code_review.md"
  fi

  if compgen -G "$ROOT/.claude/hooks/harness/acceptance-gate.*" >/dev/null 2>&1; then
    award quality_gates 2 "acceptance-gate hook"
  else
    skip quality_gates "acceptance-gate hook"
  fi

  if compgen -G "$ROOT/.claude/hooks/harness/backpressure-gate.*" >/dev/null 2>&1; then
    award quality_gates 2 "backpressure-gate hook"
  else
    skip quality_gates "backpressure-gate hook"
  fi

  if exists "rules/quality_gates.md"; then
    award quality_gates 1 "rules/quality_gates.md"
  else
    skip quality_gates "rules/quality_gates.md"
  fi

  if exists "rules/verification_tests_and_evals.md"; then
    award quality_gates 2 "rules/verification_tests_and_evals.md"
  else
    skip quality_gates "rules/verification_tests_and_evals.md"
  fi
}

# --- 4. Memory Persistence ---
score_memory_persistence() {
  if exists "rules/session_persistence.md"; then
    award memory_persistence 2 "rules/session_persistence.md"
  else
    skip memory_persistence "rules/session_persistence.md"
  fi

  if has_pattern "CLAUDE.md" "auto memory" \
    || has_pattern "CLAUDE.md" "MEMORY.md" \
    || has_pattern "CLAUDE.md" "memory system"; then
    award memory_persistence 3 "CLAUDE.md auto-memory references"
  else
    skip memory_persistence "CLAUDE.md auto-memory reference"
  fi

  if grep -rqF ".omc/state/sessions" "$ROOT/CLAUDE.md" "$ROOT/rules" 2>/dev/null; then
    award memory_persistence 2 ".omc/state/sessions referenced"
  else
    skip memory_persistence ".omc/state/sessions reference"
  fi

  # 'sum' skill mentioned in CLAUDE.md or rules
  if grep -rqwF "sum" "$ROOT/CLAUDE.md" 2>/dev/null \
    || grep -rqwF "sum" "$ROOT/rules" 2>/dev/null; then
    award memory_persistence 3 "sum skill referenced"
  else
    skip memory_persistence "sum skill reference"
  fi
}

# --- 5. Eval Coverage ---
score_eval_coverage() {
  if exists "templates/eval_definition.md"; then
    award eval_coverage 2 "templates/eval_definition.md"
  else
    skip eval_coverage "templates/eval_definition.md"
  fi

  if exists "templates/eval_report.md"; then
    award eval_coverage 2 "templates/eval_report.md"
  else
    skip eval_coverage "templates/eval_report.md"
  fi

  if exists "checklists/eval.md"; then
    award eval_coverage 2 "checklists/eval.md"
  else
    skip eval_coverage "checklists/eval.md"
  fi

  if has_pattern "rules/verification_tests_and_evals.md" "Eval-Driven Development" \
    || has_pattern "rules/verification_tests_and_evals.md" "EDD"; then
    award eval_coverage 2 "EDD section in verification rule"
  else
    skip eval_coverage "EDD section"
  fi

  if exists "eval"; then
    award eval_coverage 2 "eval/ runner directory"
  else
    skip eval_coverage "eval/ runner directory"
  fi
}

# --- 6. Security Guardrails ---
score_security_guardrails() {
  if exists "rules/safety_security.md"; then
    award security_guardrails 2 "rules/safety_security.md"
  else
    skip security_guardrails "rules/safety_security.md"
  fi

  if exists "rules/agent_security.md"; then
    award security_guardrails 2 "rules/agent_security.md"
  else
    skip security_guardrails "rules/agent_security.md"
  fi

  if compgen -G "$ROOT/.claude/hooks/harness/destructive-guard.*" >/dev/null 2>&1; then
    award security_guardrails 3 "destructive-guard hook"
  else
    skip security_guardrails "destructive-guard hook"
  fi

  if compgen -G "$ROOT/.claude/hooks/harness/mcp-gate.*" >/dev/null 2>&1; then
    award security_guardrails 2 "mcp-gate hook"
  else
    skip security_guardrails "mcp-gate hook"
  fi

  if grep -rqiF "secret" "$ROOT/rules" 2>/dev/null \
    || grep -rqiF "credential" "$ROOT/rules" 2>/dev/null; then
    award security_guardrails 1 "secret/credential keyword in rules/"
  else
    skip security_guardrails "secret/credential keyword"
  fi
}

# --- 7. Cost Efficiency ---
score_cost_efficiency() {
  if exists "rules/cost_awareness.md"; then
    award cost_efficiency 3 "rules/cost_awareness.md"
  else
    skip cost_efficiency "rules/cost_awareness.md"
  fi

  if has_pattern "CLAUDE.md" "model_routing" || has_pattern "CLAUDE.md" "model routing"; then
    award cost_efficiency 3 "CLAUDE.md model routing"
  else
    skip cost_efficiency "CLAUDE.md model routing"
  fi

  if exists "rules/context_management.md"; then
    award cost_efficiency 2 "rules/context_management.md"
  else
    skip cost_efficiency "rules/context_management.md"
  fi

  if grep -rqiF "token budget" "$ROOT/rules" 2>/dev/null \
    || grep -rqiF "token budget" "$ROOT/CLAUDE.md" 2>/dev/null \
    || grep -rqiF "token-budget" "$ROOT/rules" 2>/dev/null; then
    award cost_efficiency 2 "token budget guidance"
  else
    skip cost_efficiency "token budget guidance"
  fi
}

score_tool_coverage
score_context_efficiency
score_quality_gates
score_memory_persistence
score_eval_coverage
score_security_guardrails
score_cost_efficiency

CATS=(tool_coverage context_efficiency quality_gates memory_persistence \
      eval_coverage security_guardrails cost_efficiency)

TOTAL=0
for cat in "${CATS[@]}"; do
  var="SCORE_$cat"
  TOTAL=$(( TOTAL + ${!var} ))
done

# --- output ---
if (( TERSE )); then
  for cat in "${CATS[@]}"; do
    var="SCORE_$cat"
    echo "  $cat: ${!var}/10"
  done
  echo "TOTAL: $TOTAL/70"
else
  echo "===== Harness Audit ====="
  echo "Root: $ROOT"
  echo ""
  for cat in "${CATS[@]}"; do
    emit_category "$cat"
  done
  echo "========================="
  echo "TOTAL: $TOTAL/70"
fi
