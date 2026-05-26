# Agent Routing Policy

프로젝트 전용 서브에이전트의 호출 기준을 정의한다.
이 에이전트들은 `.claude/agents/`에 정의되어 있으며, 부모 세션의 MCP 클라이언트를 이름으로 참조한다.

## 라우팅 기준

### 판단 흐름

```
작업에 외부 정보(웹/문서) 필요?
  → Yes → researcher
작업에 DB 접근(스키마/데이터) 필요?
  → Yes → db-worker
작업에 심볼 기반 리팩터링(rename/references) 필요?
  → Yes → refactorer
위 중 2개 이상 동시 필요?
  → Yes → full-context
어디에도 해당 안 됨?
  → 직접 처리 또는 빌트인 에이전트 사용

구현 완료 후 검증 필요?
  → verifier (AC/하네스 기반 완료 검증)
코드 변경의 품질 리뷰 필요?
  → reviewer (3-pass 적대적 리뷰)
```

### 에이전트별 트리거

| 에이전트 | MCP | 트리거 조건 | 비트리거 (직접 처리) |
|----------|-----|-------------|---------------------|
| **researcher** | Exa | 외부 API 문서 조회, 에러 메시지 검색, 최신 릴리스 확인, 기술 비교 조사 | 이미 알고 있는 정보, 프로젝트 내부 코드 탐색 |
| **db-worker** | Supabase | 테이블 스키마 조회, 데이터 쿼리, 마이그레이션 생성, RLS 정책 확인 | 코드 내 타입 정의만 보면 되는 경우 |
| **refactorer** | Serena | 3+ 파일에 걸친 심볼 rename, 인터페이스 변경의 영향 범위 확인, safe delete | 단일 파일 내 변수명 변경, 텍스트 치환으로 충분한 경우 |
| **full-context** | Exa+Supabase+Serena+Context7 | 새 외부 SDK 도입 + DB 스키마 변경 + 코드 리팩터링이 한 작업에 얽힌 경우 | 단일 도메인 작업 (위 3개 중 하나로 충분) |
| **reviewer** | — | 코드 변경 후 품질 리뷰 (3-pass: self + Codex + OMC) | 단순 문서/설정 변경 |
| **verifier** | — | 구현 완료 주장 전 AC/하네스/테스트 검증 | AC가 정의되지 않은 탐색적 작업 |

### 검증 에이전트 호출 기준

- **reviewer**: SHOULD 코드 변경이 10줄 이상이거나 로직 변경을 포함할 때 호출. 결과는 `docs/reviews/`에 자동 기록.
- **verifier**: MUST 작업 완료를 사용자에게 보고하기 전에 호출. AC가 있는 경우 필수.

### MCP 도구 에이전트 강도

- **MUST delegate**: db-worker로 DDL 변경 (직접 Supabase MCP 호출 금지)
- **SHOULD delegate**: researcher로 외부 정보 조회 (빌트인 WebSearch로도 가능하나 Exa가 더 정확)
- **MAY delegate**: refactorer로 리팩터링 (OMC LSP로도 가능하나 Serena가 의미 편집 지원)

## 병렬 실행 가이드

독립적인 서브태스크가 2개 이상이면 병렬 호출한다:

```
예: "Stripe SDK 문서 확인하고, 결제 테이블 스키마도 봐줘"
  → researcher (Stripe 문서) + db-worker (payments 테이블) 동시 호출
```

단, 의존 관계가 있으면 순차:

```
예: "최신 Stripe webhook 스펙 확인 후 그에 맞게 테이블 수정해"
  → researcher 먼저 → 결과 기반으로 db-worker
```

## 모델 정책

현재 모든 에이전트가 `opus`로 설정됨. 사용량이 rate limit에 근접하면 아래 순서로 다운그레이드:

1. researcher → sonnet (검색 결과 요약은 sonnet으로 충분)
2. refactorer → sonnet (기계적 rename은 sonnet으로 충분)
3. db-worker → 유지 (DDL 실수 방지)
4. full-context → 유지 (복합 판단 필요)
