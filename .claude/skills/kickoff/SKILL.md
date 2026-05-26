---
name: kickoff
allowed-tools: Read, Write, Glob, Grep, Bash(cat:*), Bash(ls:*), Bash(echo:*), Bash(date:*), AskUserQuestion
argument-hint: [project name or feature description]
description: Project/feature kickoff interview (JTBD -> Context -> Scope -> Acceptance -> Backpressure)
---

# Kickoff - Project/Feature Start Interview

## Goal

Gather essential information before any implementation begins. Ensures work starts with clear purpose, scope, and success criteria.

No coding. Only information gathering + state file saving to `docs/harness/`.

## Non-Negotiables

| Rule | Violation = STOP |
|------|------------------|
| **No implementation** | This is interview only |
| **No guessing** | Discover from repo, not assume |
| **All 5 phases required** | Cannot skip phases |
| **User confirmation per phase** | Each phase needs explicit approval |
| **Output must be saved** | Kickoff summary required |

## Inputs

- `$ARGUMENTS`: Project name or feature description
  - `"새 프로젝트"` / `"new project"` → full kickoff (Vision + all phases)
  - `"로그인 기능"` / `"add feature X"` → feature kickoff (skip Vision, start at JTBD)

## Workflow

### Phase 0: JTBD (Job To Be Done)

**질문** (AskUserQuestion 도구 사용):
1. 이 작업의 최종 사용자는 누구인가?
2. 사용자가 해결하려는 문제는 무엇인가?
3. 성공했을 때 사용자의 상태는 어떻게 달라지는가?

**Gate**: 성공 기준이 1-2문장으로 정리될 때까지 진행하지 않음

**Output**:
```markdown
### JTBD
- User: <who>
- Problem: <what>
- Success: <measurable outcome>
```

---

### Phase 1: Context Discovery

**Agent가 수행** (사용자에게 묻지 않음):
1. 프로젝트 구조 파악 (Glob, Read)
2. 기존 패턴 확인 (package.json, CLAUDE.md, README)
3. 기술 스택 확인
4. 빌드/테스트/린트 명령어 발견

**Gate**: 증거 없이 추측하지 않음. 모르면 "확인 필요"로 표시.

**Output**:
```markdown
### Context
- Repo type: <monorepo/single/docs-only>
- Tech stack: <discovered or "N/A">
- Build cmd: <discovered or "N/A">
- Test cmd: <discovered or "N/A">
- Existing patterns: <list or "none found">
- Risks/constraints: <list>
```

---

### Phase 2: Scope Definition

**질문** (AskUserQuestion 도구 사용):
1. 이번에 반드시 해야 하는 것은? (MUST)
2. 하면 좋지만 필수는 아닌 것은? (SHOULD)
3. 명시적으로 하지 않을 것은? (MUST NOT)
4. 관련 있지만 별도 처리할 것은? (OUT OF SCOPE)

**Gate**: MUST가 최소 1개, OUT OF SCOPE가 최소 1개 정의될 때까지

**Output**:
```markdown
### Scope
- MUST: <list>
- SHOULD: <list>
- MUST NOT: <list>
- OUT OF SCOPE: <list>
```

---

### Phase 3: Acceptance Criteria

**질문** (AskUserQuestion 도구 사용):
1. 이 기능이 동작한다는 것을 어떻게 증명할 수 있는가?
2. 엣지 케이스는 무엇인가?
3. 실패 시나리오는 어떻게 처리해야 하는가?

**Gate**: 최소 3개의 구체적인 수락 기준이 정의될 때까지

**Output**:
```markdown
### Acceptance Criteria
1. <specific, testable criterion>
2. <specific, testable criterion>
3. <specific, testable criterion>

### Edge Cases
- <case 1>
- <case 2>
```

---

### Phase 4: Backpressure Setup

**Agent가 확인 + 사용자 질문**:
1. Context에서 발견한 테스트/빌드 명령어 확인
2. 자동화된 검증이 없으면 → 수동 검증 방법 질문

**Gate**: 검증 방법이 최소 1개 정의될 때까지

**Output**:
```markdown
### Backpressure
- Verification method: <test cmd / manual checklist / rubric>
- How to run: <command or steps>
```

---

### Completion: Save & Signal (MANDATORY)

**⚠️ 이 단계를 건너뛰면 안 됨. 반드시 모든 Step을 완료해야 kickoff 완료.**

#### Step 1: kickoff-done 플래그 생성
```bash
echo "$(date -Iseconds)" > docs/harness/kickoff-done
```

#### Step 2: kickoff-summary.md 저장
Write 도구로 `docs/harness/kickoff-summary.md`에 아래 Output Format 전체 저장.

#### Step 3: seed.yaml 생성

`docs/templates/seed.template.yaml`을 참조하여 `docs/harness/seed.yaml`을 생성한다.

**필드 매핑:**
- `version`: 1
- `status`: draft
- `task_id`: 자동 생성 (`YYYYMMDD-HHMMSS-<4자리 랜덤 hex>`, Bash `date +%Y%m%d-%H%M%S`-`openssl rand -hex 2`)
- `goal`: Phase 0 JTBD의 Success 기준에서 추출
- `constraints`: Phase 2 MUST NOT + Phase 1에서 발견한 기술 제약
- `acceptance_criteria`: Phase 3의 모든 수락 기준
- `out_of_scope`: Phase 2 OUT OF SCOPE
- `assumptions`: Phase 1 Context 중 증거 없이 전제한 항목
- `risks`: Phase 1 Risks + Phase 3 Edge Cases
- `references`: kickoff-summary.md + 관련 파일 경로

**생성 후 자체 검증:**
- YAML 파싱 가능한가 (Read로 다시 읽어서 확인)
- 필수 필드 10개 (version, status, task_id, goal, constraints, acceptance_criteria, out_of_scope, assumptions, risks, references) 모두 존재하는가
- acceptance_criteria가 1개 이상인가
- `docs/rules/seed_contract.md` 기준에 부합하는가

#### Step 3.5: Plan Attack Gate (적대적 검증)

seed.yaml 생성 후 자동 실행. 정책: [`rules/adversarial_review.md`](../../../rules/adversarial_review.md)

```
1. audit.jsonl에서 현재 task_id의 adversarial_plan_attack 이벤트 수를 세어 run_count 결정
2. critic 에이전트 (opus) 호출:
   - seed.yaml 전체를 입력으로 제공
   - 구조적 공격 템플릿:
     a) "이 goal이 달성 불가능한 이유 3가지"
     b) "이 acceptance criteria가 불충분한 이유"
     c) "이 scope에서 빠진 치명적 항목"
   - 각 발견에 심각도 부여 (CRITICAL / HIGH / MEDIUM)
   - CRITICAL 판정 기준: 3조건 동시 충족
     (1) 요구사항 미충족/보안 취약점/데이터 손실 가능성
     (2) 수정 없이 진행하면 후속 단계에서 반드시 실패
     (3) 구체적 증거 제시 (seed.yaml 필드 인용)
3. 결과를 docs/harness/plan-attack-report.md에 저장
4. audit.jsonl에 append:
   {"ts":"<ISO>","event":"adversarial_plan_attack","actor":"critic","meta":{"task_id":"<id>","run_count":<N>,"result":"<PASS|WARN|BLOCK>","findings":[...]}}
5. 판정:
   - run_count=1: WARN (결과를 사용자에게 표시, 진행 가능)
   - run_count≥2: CRITICAL 발견 시 BLOCK → 사용자에게 보완 요구
     - 사용자가 "그냥 진행해" → override 허용
     - audit.jsonl에 adversarial_override 이벤트 기록
   - CRITICAL 없으면: PASS
```

#### Step 4: Rubric 판정

seed.yaml 내용을 기반으로 4개 차원을 판정한다.

| 차원 | HIGH | MEDIUM | LOW |
|------|------|--------|-----|
| `goal_clarity` | 구현 결과가 구체적으로 보임 | 목표는 있으나 약간 모호 | 추상적이거나 목표 없음 |
| `constraint_clarity` | 제약이 구체적이고 실행 가능 | 제약 있으나 일부 모호 | 제약 없거나 전부 모호 |
| `success_criteria_clarity` | 모든 AC가 테스트/관찰 가능 | 일부만 테스트 가능 | 테스트 가능한 AC 없음 |
| `context_clarity` | 기술 스택, 패턴, 참조 충분 | 부분적 컨텍스트 | 최소한의 발견 |

결과를 `docs/templates/rubric-report.template.md` 형식에 맞춰 `docs/harness/rubric-report.md`에 저장.

#### Step 5: Rubric 결과 처리

- 전부 HIGH 또는 MEDIUM → "통과. startdev 진행 가능"
- LOW가 1개 이상 →
  - AskUserQuestion으로 해당 차원의 보완 질문을 던진다
  - 보완 후 → seed.yaml 갱신, rubric 재판정
  - 사용자가 명시적으로 "그냥 진행해" → override 허용
    - `rubric-report.md`의 Override Reason에 사유 기록
    - `audit.jsonl`에 `seed_override_approved` 이벤트 기록

#### Step 6: current-scope.md 저장 (호환성 유지)
Write 도구로 `docs/harness/current-scope.md`에 Scope 섹션만 추출하여 저장:

```markdown
# Current Scope: <project/feature name>

**Created**: <date>

## MUST
<list>

## SHOULD
<list>

## MUST NOT
<list>

## OUT OF SCOPE
<list>

## Acceptance Criteria
- [ ] <AC 1>
- [ ] <AC 2>
- [ ] <AC 3>
```

> **참고**: current-scope.md는 기존 훅 호환성을 위해 유지한다. seed.yaml이 권위 있는 원본이며, current-scope.md는 파생물이다.

#### Step 7: audit.jsonl 기록

`docs/harness/audit.jsonl`에 아래 이벤트를 append한다 (한 줄에 JSON 하나):

```
{"ts":"<ISO>","event":"kickoff_completed","actor":"assistant","meta":{"topic":"<작업 주제>"}}
{"ts":"<ISO>","event":"seed_generated","actor":"assistant","meta":{"seed_path":"docs/harness/seed.yaml","status":"draft","version":1}}
{"ts":"<ISO>","event":"rubric_evaluated","actor":"assistant","meta":{"goal":"<H/M/L>","constraints":"<H/M/L>","success":"<H/M/L>","context":"<H/M/L>"}}
```

override가 있었다면 추가:
```
{"ts":"<ISO>","event":"seed_override_approved","actor":"user","meta":{"reason":"<사유>"}}
```

> **주의**: 기존 audit.jsonl 내용을 덮어쓰지 말고 반드시 append. Bash `echo '...' >> docs/harness/audit.jsonl` 또는 기존 내용을 Read한 후 합쳐서 Write.

#### Step 8: README placeholder 채우기 (조건부)

`/init`이 만든 placeholder를 kickoff 결과로 채운다. **사용자가 이미 손댔으면 건드리지 않는다**.

**판별**:
- `README.md`에 `<!-- claude-template-placeholder -->` 마커가 있으면 placeholder 상태 → 채움
- 마커가 없으면 사용자가 수정한 것 → 건드리지 않고 Step 9로

**채움 (placeholder인 경우)**:

`README.md`을 아래 형식으로 덮어쓴다 (project name은 git remote 또는 디렉토리명에서 추출):

```markdown
**[English](README.en.md)**

# <project-name>

<JTBD.Success를 1-2문장으로 풀어쓴 한 줄 설명>

## 목표

<seed.yaml의 goal 필드>

## 수락 기준

- [ ] <AC 1>
- [ ] <AC 2>
- [ ] <AC 3>

## 제약

<seed.yaml의 constraints 항목들 — 없으면 섹션 생략>

## 상태

🚧 개발 중 — 자세한 컨텍스트는 `docs/harness/kickoff-summary.md` 참고.
```

`README.en.md`도 동일 구조로, 영문으로 덮어쓴다 (마커가 있는 경우에 한해):

```markdown
**[한국어](README.md)**

# <project-name>

<English one-liner from JTBD.Success>

## Goal

<goal>

## Acceptance Criteria

- [ ] <AC 1>
...

## Constraints

<list — omit section if empty>

## Status

🚧 In development — see `docs/harness/kickoff-summary.md` for full context.
```

> 영문 번역은 한국어 원문을 자연스러운 영어로 옮긴다. 기계 번역체 금지.

**audit 기록**:
```
{"ts":"<ISO>","event":"readme_initialized","actor":"assistant","meta":{"source":"kickoff"}}
```

마커가 없어 건너뛴 경우:
```
{"ts":"<ISO>","event":"readme_initialized","actor":"assistant","meta":{"skipped":"user_modified"}}
```

#### Step 9: 다음 단계 안내
저장 완료 후 출력:
> "Kickoff 완료. seed.yaml 생성됨 (status: draft). 구현을 시작하려면 `/startdev`를 사용하세요."

---

## Output Format

```markdown
## Kickoff Summary: <project/feature name>

**Date**: YYYY-MM-DD
**Type**: New Project / Feature

### JTBD
- User: <who>
- Problem: <what>
- Success: <measurable outcome>

### Context
- Repo type: <type>
- Tech stack: <stack>
- Build/Test: <commands>
- Patterns: <list>

### Scope
- MUST: <list>
- SHOULD: <list>
- MUST NOT: <list>
- OUT OF SCOPE: <list>

### Acceptance Criteria
1. <criterion>
2. <criterion>
3. <criterion>

### Backpressure
- Method: <verification>
- Command: <how to run>

---
Kickoff complete. Ready for implementation.
Next: `/startdev` or manual planning.
```

## State Management

| File | Purpose | When |
|------|---------|------|
| `docs/harness/kickoff-done` | Flag that kickoff completed | Created at end |
| `docs/harness/kickoff-summary.md` | 사람 중심 요약 | Created at end |
| `docs/harness/seed.yaml` | 하네스 중심 구조화 명세 (1급 입력) | Created at end |
| `docs/harness/plan-attack-report.md` | 적대적 계획 검증 결과 | Created at Step 3.5 |
| `docs/harness/rubric-report.md` | 명확도 4차원 판정 보고서 | Created at end |
| `docs/harness/current-scope.md` | 훅 호환용 scope 정의 (파생물) | Created at end |
| `docs/harness/audit.jsonl` | Append-only 감사 로그 | Appended throughout |

## Integration with Hooks

- **kickoff-detector** (UserPromptSubmit): 새 작업 감지 시 "/kickoff 먼저 실행하세요" 리마인더
- **scope-gate** (PreToolUse): seed.yaml의 out_of_scope 기반으로 경로 변경 블록 (current-scope.md fallback)
- **acceptance-gate** (PreToolUse): git commit 시 Acceptance criteria 미충족이면 블록

## Contracts

- `docs/rules/seed_contract.md` — seed.yaml 스키마 및 유효성 규칙
- `docs/rules/kickoff_output_contract.md` — kickoff 산출물 정의
- `docs/rules/startdev_seed_contract.md` — startdev가 seed.yaml을 읽는 방법

## References

- `assets/kickoff_checklist.md` — 전체 체크리스트
- `temp/harness-master.md` — Harness 설계 문서

## Patterns Applied

`constraints_first`, `explicit_output_schema`, `staged_workflow`, `human_in_the_loop`, `evidence_first`
