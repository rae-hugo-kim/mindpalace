# Seed Contract

## Purpose
`seed.yaml`은 `kickoff`의 구조화 산출물이며, `startdev`와 후속 검증 단계가 공통으로 읽는 1급 입력이다.

이 문서의 목표는 다음 두 가지다.

- 사람이 읽는 요약과 별개로, 하네스가 기계적으로 해석 가능한 명세 형식을 고정한다.
- `startdev`, 검증, scope gate, anti-hallucination 규칙이 동일한 기준을 보도록 만든다.

## Scope
이 계약은 `docs/harness/seed.yaml`에 적용된다.

비목표:
- DDD 수준의 복잡한 `ontology_schema`
- event sourcing
- generation loop
- 별도 MCP 백엔드

## Required Fields

필수 필드:

- `version`
- `status`
- `task_id`
- `goal`
- `constraints`
- `acceptance_criteria`
- `out_of_scope`
- `assumptions`
- `risks`
- `references`

## Field Semantics

### `version`
- 정수
- 초기값은 `1`
- 구조가 바뀌면 증가

### `task_id`
- 문자열
- kickoff 시 자동 생성
- 형식: `YYYYMMDD-HHMMSS-<4자리 랜덤 hex>`
- 동일 태스크의 재실행 구분에 사용 (audit.jsonl과 연결)
- 수동 편집하지 않는다

### `status`
- 허용값: `draft`, `approved`, `superseded`
- `kickoff` 직후 기본값은 `draft`

### `goal`
- 한 문단 또는 짧은 여러 줄 텍스트
- "무엇을 만들거나 바꾸는지"를 결과 중심으로 적는다

### `constraints`
- 문자열 배열
- 반드시 지켜야 하는 기술/운영/정책 제약

### `acceptance_criteria`
- 문자열 배열
- 완료 여부를 검증 가능한 문장으로 적는다
- 모호한 표현 대신 관찰 가능한 결과를 쓴다

### `out_of_scope`
- 문자열 배열
- 이번 작업에서 하지 않는 일
- scope drift 방지용 필수 항목

### `assumptions`
- 문자열 배열
- 증거가 아니라 현재 전제하는 사항
- anti-hallucination 규칙과 연결되는 핵심 필드

### `risks`
- 문자열 배열
- 실패 가능성, 회귀 위험, 검증 사각지대

### `references`
- 객체 배열
- 각 객체는 최소 `path`, `reason`을 가진다

예:

```yaml
references:
  - path: docs/harness/kickoff-summary.md
    reason: 원본 킥오프 요약
```

## Authoring Rules

- `goal`은 하나여야 한다. 여러 목표를 한 파일에 섞지 않는다.
- `constraints`와 `out_of_scope`는 분리한다.
- `acceptance_criteria`는 최소 1개 이상이어야 한다.
- `assumptions`는 사실처럼 쓰지 말고 전제로 명시한다.
- `risks`는 없더라도 빈 배열로 남긴다.
- `references`는 가능하면 실제 파일 경로를 가리킨다.

## Validation Rules

아래 조건을 만족하지 않으면 유효하지 않다.

- YAML 파싱 가능
- 필수 필드 10개 모두 존재 (version, status, task_id, goal, constraints, acceptance_criteria, out_of_scope, assumptions, risks, references)
- `task_id` 형식 일치 (`YYYYMMDD-HHMMSS-XXXX`)
- `acceptance_criteria` 길이 >= 1
- `out_of_scope`, `assumptions`, `risks`, `references`는 배열
- `status`가 허용값 중 하나

## Operational Rules

- `kickoff`는 `seed.yaml`을 생성하거나 갱신한다.
- `startdev`는 `seed.yaml`을 우선 입력으로 읽는다.
- `seed.yaml`이 없으면 `startdev`는 실패하거나 `kickoff`를 요구해야 한다.
- 사람이 읽는 설명은 `kickoff-summary.md`에 남기고, 실행 판단은 `seed.yaml` 기준으로 한다.

## Anti-Patterns

- 산문만 길고 `acceptance_criteria`가 비어 있는 seed
- 제약과 비범위를 섞어 쓰는 seed
- 가정을 증거처럼 서술하는 seed
- 참조 파일 없이 추상 문장만 있는 seed

## Minimal Example

```yaml
version: 1
status: draft
task_id: "20260401-143000-a1b2"

goal: >
  기존 API에 토큰 기반 인증을 추가한다.

constraints:
  - 공개 엔드포인트 동작은 유지한다
  - 수동 검증 절차를 남긴다

acceptance_criteria:
  - 인증이 필요한 엔드포인트는 인증 없이 401을 반환한다
  - 유효한 토큰으로 요청 시 정상 응답을 반환한다

out_of_scope:
  - OAuth 도입

assumptions:
  - 기존 서버 구조에 인증 미들웨어를 추가할 수 있다

risks:
  - 공개 엔드포인트까지 실수로 보호될 수 있다

references:
  - path: docs/harness/kickoff-summary.md
    reason: 원본 요약
```
