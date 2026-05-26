<!-- policy-sync-warning:start -->
warning_type: reference_only
non_normative_reference_only: true
last_sync_date: 2026-03-31
status: synced
source_of_truth: ../CLAUDE.md
source_commit_hash: aafe3e1a5c6768da2aa652ef93330b3374808143
<!-- policy-sync-warning:end -->

# CLAUDE.md (에이전트 규칙 - 계층형)

이 파일은 **항상-on(always-on)** 에이전트 정책입니다. 짧게 유지합니다.

## 네비게이션

- 여기부터 읽고, 아래 인덱스로 이동합니다:
  - `INDEX.md`
  - `rules/INDEX.md`
  - `checklists/INDEX.md`
  - `templates/INDEX.md`

## 적용 범위

- 이 정책은 에이전트가 활성화되어 있는 동안 이 레포/워크스페이스에 적용됩니다.
- 링크된 모듈 문서가 이 파일과 충돌하면, **이 파일을 우선**합니다.
- **이 정책은 oh-my-claudecode 글로벌 규칙을 보완합니다** (대체하지 않음).

## oh-my-claudecode 통합

이 레포는 **oh-my-claudecode**가 전역으로 활성화되어 있다고 가정합니다. 다음 항목들은 자동으로 적용됩니다:

| 항목 | 방법 | 훅 위치 |
|------|------|---------|
| 코드 변경 | executor 에이전트에 위임 | N/A (글로벌 규칙) |
| 범위 적용 | `scope-gate` 훅 | `.claude/hooks/harness/` |
| 편집 전 파일 읽기 | `context-gate` + `read-tracker` 훅 | `.claude/hooks/harness/` |
| 완료 검증 | Architect 에이전트 | N/A (글로벌 규칙) |
| 실패 시 배압 | `backpressure-gate` + `backpressure-tracker` 훅 | `.claude/hooks/harness/` |
| 인수 기준 | `acceptance-gate` 훅 | `.claude/hooks/harness/` |
| 신규 작업 감지 | `kickoff-detector` 훅 | `.claude/hooks/harness/` |

모든 훅은 `.claude/settings.json`에 등록되어 있으며 이 레포에 포함되어 있습니다.

**이 파일이 추가하는 것**: 프로젝트별 제약 사항, 증거 기준, 문서 요건.

Harness 검증 계약 세부 사항: [`rules/harness_integration_contract.md`](../rules/harness_integration_contract.md)

## 용어 (RFC 2119)

- **MUST**: 필수. 준수할 수 없으면 Exception Protocol을 따릅니다.
- **SHOULD**: 기본 기대치. 짧은 근거가 있으면 생략할 수 있습니다.
- **MAY**: 선택 사항.

## 우선순위 (충돌 해결)

1) **안전 & 보안**
2) **레포의 사실(Repo Truth)** (lockfiles / manifests / CI / repo docs)
3) **검증(Verification)** (tests/evals/재현 가능한 절차)
4) **변경 통제(Change Control)** (최소 변경, 범위 제한된 diff)
5) **유지보수성(Maintainability)** (가독성, tidy 리팩토링)

## 핵심 원칙

### 1. 코딩 전에 생각하기
- 가정을 명시적으로 밝힙니다. 불확실하면 질문합니다.
- 여러 해석이 가능하면 모두 제시합니다 — 조용히 하나를 선택하지 않습니다.
- 더 단순한 접근법이 있으면 말합니다. 필요하면 반론을 제기합니다.
- → 세부 사항: [`rules/anti_hallucination.md`](../rules/anti_hallucination.md)

### 2. 단순함 우선
- 요청된 것 이상의 기능을 추가하지 않습니다. 단일 사용 코드에는 추상화를 쓰지 않습니다.
- 200줄을 50줄로 쓸 수 있다면 다시 씁니다.
- 자가 점검: "시니어 엔지니어가 이게 과도하게 복잡하다고 할까?"
- → 세부 사항: [`rules/change_control.md`](../rules/change_control.md)

### 3. 외과적 변경
- 사용자의 요청에 직접 연결되는 줄만 수정합니다.
- 기존 스타일을 맞춥니다. 인접 코드를 "개선"하지 않습니다.
- 관련 없는 문제를 발견하면 언급하되 — 수정하지 않습니다.
- → 세부 사항: [`rules/change_control.md`](../rules/change_control.md)

### 4. 목표 기반 실행
- 모호한 작업을 성공 기준이 있는 검증 가능한 목표로 변환합니다.
- "버그를 고쳐" → "버그를 재현하는 테스트를 작성하고, 통과시킨다"
- 각 단계는 다음 형태여야 합니다: [행동] → 검증: [확인]
- → 세부 사항: [`rules/verification_tests_and_evals.md`](../rules/verification_tests_and_evals.md), [`rules/tdd_policy.md`](../rules/tdd_policy.md)

## 양보 불가 항목 (MUST)

- **추측 금지**: 버전, 커맨드, API, 파일을 발명하지 않습니다.
- **레포 커맨드**: build/test/lint/typecheck/e2e/eval 커맨드를 추측하지 않습니다. 레포에서 찾아 사용합니다.
- **위험 작업**: 위험한 변경을 제안/실행하기 전에 명시적 승인을 받습니다.
- **검증**: 사용자 영향 변경은 최소 1개의 재현 가능한 검증 아티팩트가 있어야 합니다.
- **문서/정책 전용 모드**: 순수 마크다운/정책/템플릿 편집의 경우, `rules/verification_tests_and_evals.md`의 docs-only 검증 경로를 따르고 필요한 증거 형식을 포함합니다.
- **근거 제시**: 핵심 결정은 구체적 근거(파일 경로 + 발췌 또는 커맨드 출력)를 함께 제공합니다.
- **Reference doc sync**: 동일한 PR에서 `claudedocs/CLAUDEKR.md`와 `claudedocs/CLAUDE_original.md`를 업데이트하거나, 명시적으로 stale로 표시합니다.

## 완료 보고 계약 (MUST)

작업이 "완료"되었다고 주장할 때, 최종 메시지에 아래 항목을 반드시 포함합니다:

- **적용한 규칙**: 어떤 규칙/체크리스트를 적용했는지
- **근거**: 핵심 주장에 대한 구체적 근거(파일 경로 + 발췌 또는 커맨드 출력)
- **검증**: 무엇으로 검증했는지(커맨드/결과)

**참고**: Architect 검증은 oh-my-claudecode 글로벌 규칙이 처리합니다. 이 계약은 완료 보고서의 *내용*을 정의합니다.

## 예외 프로토콜 (막혔을 때 MUST)

어떤 MUST도 준수할 수 없는 경우:

1) **이유**를 설명합니다(무엇이 준수를 막는지).
2) **대안 2–3개**를 제시합니다(안전한 옵션만).
3) 대안이 위험하거나 되돌리기 어려우면 **명시적 확인**을 요청합니다.

## MCP 서버 정책 (트리거 기반)

- 전체 정책은 [`rules/mcp_policy.md`](../rules/mcp_policy.md)를 참조합니다.
- **Context7**: 새로운 외부 API/SDK, 의존성, 버전 민감 문법에는 MUST 사용.
- **Serena**: 심볼 탐색, 리팩토링, 코드 이해에 SHOULD 사용.
- **Supabase**: DDL에는 MUST 마이그레이션 사용; 쿼리에는 MAY 직접 SQL 사용.
- **Web Search**: 최신 이벤트, 오류, 최신 문서에 SHOULD 사용.

## 연결된 모듈

- Safety & security: [`rules/safety_security.md`](../rules/safety_security.md)
- Anti-hallucination & evidence: [`rules/anti_hallucination.md`](../rules/anti_hallucination.md)
- Repo command discovery: [`rules/repo_command_discovery.md`](../rules/repo_command_discovery.md)
- MCP server policies: [`rules/mcp_policy.md`](../rules/mcp_policy.md)
- Context7 trigger policy: [`rules/context7_policy.md`](../rules/context7_policy.md)
- Verification (tests + evals): [`rules/verification_tests_and_evals.md`](../rules/verification_tests_and_evals.md)
- Change control (minimal change, scope, tidy): [`rules/change_control.md`](../rules/change_control.md)
- Documentation policy (optional): [`rules/documentation_policy.md`](../rules/documentation_policy.md)
- Assetization (spec/decision/retro): [`rules/assetization.md`](../rules/assetization.md)
- Commit/PR discipline: [`rules/commit_and_pr.md`](../rules/commit_and_pr.md)
- TDD policy: [`rules/tdd_policy.md`](../rules/tdd_policy.md)
- Harness integration contract: [`rules/harness_integration_contract.md`](../rules/harness_integration_contract.md)
- Code review policy: [`rules/code_review_policy.md`](../rules/code_review_policy.md)
- Quality gates: [`rules/quality_gates.md`](../rules/quality_gates.md)
- Context management: [`rules/context_management.md`](../rules/context_management.md)
- Cost awareness: [`rules/cost_awareness.md`](../rules/cost_awareness.md)
- Learning policy: [`rules/learning_policy.md`](../rules/learning_policy.md)
- Coding standards: [`rules/coding_standards.md`](../rules/coding_standards.md)
- Agent security: [`rules/agent_security.md`](../rules/agent_security.md)
- Hook recipes: [`rules/hook_recipes.md`](../rules/hook_recipes.md)
- Session persistence: [`rules/session_persistence.md`](../rules/session_persistence.md)

## 체크리스트 (필요 시 사용)

- Planning: [`checklists/plan.md`](../checklists/plan.md)
- Verification: [`checklists/verify.md`](../checklists/verify.md)
- Risky actions: [`checklists/risky_actions.md`](../checklists/risky_actions.md)
- Bugfix protocol: [`checklists/bugfix.md`](../checklists/bugfix.md)
- PR body: [`checklists/pr.md`](../checklists/pr.md)
- Code review: [`checklists/code_review.md`](../checklists/code_review.md)
- Quality gate: [`checklists/quality_gate.md`](../checklists/quality_gate.md)
- Eval (EDD): [`checklists/eval.md`](../checklists/eval.md)
- Research before implement: [`checklists/research_before_implement.md`](../checklists/research_before_implement.md)

## 템플릿

- Assumptions: [`templates/assumptions.md`](../templates/assumptions.md)
- Change log: [`templates/decision_log.md`](../templates/decision_log.md)
- PR description: [`templates/pr_body.md`](../templates/pr_body.md)
- Retro note: [`templates/retro.md`](../templates/retro.md)
- Eval definition: [`templates/eval_definition.md`](../templates/eval_definition.md)
- Eval report: [`templates/eval_report.md`](../templates/eval_report.md)
- Session retro: [`templates/session_retro.md`](../templates/session_retro.md)
