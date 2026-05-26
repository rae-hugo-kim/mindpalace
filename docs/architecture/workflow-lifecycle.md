# 작업 라이프사이클 — 하네스 기반 전체 흐름

> Generated: 2026-04-24 | Harness v2026.7

## 1. 전체 흐름 (한눈에)

```mermaid
flowchart TD
    START([세션 시작]) --> HVC[harness-version-check<br/>하네스 드리프트 확인]
    HVC --> USER_INPUT[사용자 요청 입력]
    
    USER_INPUT --> KD{kickoff-detector<br/>새 작업인가?}
    KD -->|새 작업 감지| KICKOFF[킥오프 단계<br/>scope·AC·seed.yaml 정의]
    KD -->|기존 작업 계속| PLAN[계획 단계]
    KICKOFF --> PLAN
    
    PLAN --> IMPL[구현 단계]
    
    IMPL --> EDIT{Edit/Write 시도}
    EDIT --> SG{scope-gate<br/>범위 내인가?}
    SG -->|OUT OF SCOPE| BLOCK_SCOPE[❌ 차단<br/>범위 이탈]
    SG -->|IN SCOPE| CG{context-gate<br/>파일 열람했나?}
    CG -->|미열람| BLOCK_CTX[❌ 차단<br/>먼저 Read]
    CG -->|열람됨| DO_EDIT[✅ 편집 실행]
    
    DO_EDIT --> READ_TRACK[read-tracker<br/>열람 기록 갱신]
    READ_TRACK --> MORE{더 구현할 것?}
    MORE -->|Yes| IMPL
    MORE -->|No| VERIFY_PHASE

    subgraph VERIFY_PHASE[검증 단계]
        TEST[빌드/테스트 실행] --> BP_TRACK[backpressure-tracker<br/>PASS 기록]
        BP_TRACK --> REVIEW[reviewer 호출<br/>3-pass 적대적 리뷰]
        REVIEW --> REVIEW_DOC[docs/reviews/ 기록]
        REVIEW_DOC --> VERIFIER[verifier 호출<br/>AC/하네스 검증]
    end

    VERIFY_PHASE --> COMMIT{git commit 시도}
    
    COMMIT --> AG{acceptance-gate<br/>AC 충족?}
    AG -->|미충족| BLOCK_AC[❌ 차단<br/>AC 미완료]
    AG -->|충족| BG{backpressure-gate<br/>테스트 통과?}
    BG -->|risk=low 문서만| SKIP_BP[통과]
    BG -->|risk≥medium 미통과| BLOCK_BP[❌ 차단<br/>테스트 먼저]
    BG -->|PASS| RG{review-gate<br/>리뷰 상태?}
    SKIP_BP --> RG
    RG -->|risk=low| SKIP_RV[통과]
    RG -->|risk≥high 리뷰 없음| BLOCK_RV[❌ 차단<br/>리뷰 먼저]
    RG -->|리뷰 PASS| COMMIT_OK[✅ 커밋 성공]
    SKIP_RV --> COMMIT_OK
    
    COMMIT_OK --> BUMP[harness-version-bump<br/>하네스 파일 변경 시 자동]
    BUMP --> DONE([완료])

    BLOCK_SCOPE --> IMPL
    BLOCK_CTX --> IMPL
    BLOCK_AC --> IMPL
    BLOCK_BP --> TEST
    BLOCK_RV --> REVIEW

    style VERIFY_PHASE fill:#0f3460,stroke:#16213e,color:#eee
    style BLOCK_SCOPE fill:#8b0000,color:#fff
    style BLOCK_CTX fill:#8b0000,color:#fff
    style BLOCK_AC fill:#8b0000,color:#fff
    style BLOCK_BP fill:#8b0000,color:#fff
    style BLOCK_RV fill:#8b0000,color:#fff
    style COMMIT_OK fill:#006400,color:#fff
```

## 2. 단계별 상세

### 2.1 세션 시작

```
사용자가 Claude Code 세션을 시작
  → [SessionStart] harness-version-check 실행
    → 로컬 하네스 버전 vs 리모트 최신 태그 비교
    → 드리프트 있으면 알림 (24시간 캐시)
  → 시스템 프롬프트에 CLAUDE.md 로드
    → Agent Routing Policy, MCP Policy 등 활성화
```

여기서 결정되는 것: 메인 에이전트가 어떤 규칙 체계 아래에서 동작하는지.

### 2.2 킥오프 (새 작업 감지 시)

```
사용자: "새 결제 기능 만들어줘"
  → [UserPromptSubmit] kickoff-detector가 패턴 감지
    → "새 기능" 키워드 + kickoff-done 파일 없음
    → advisory: "킥오프 먼저 하세요"
  
  → 메인 에이전트가 사용자와 대화형 인터뷰
    → Goal, Constraints, AC, Out of Scope, Assumptions 정의
    → docs/harness/seed.yaml 생성
    → docs/harness/kickoff-done 생성
```

여기서 결정되는 것:
- **scope-gate**가 참조할 OUT OF SCOPE 목록
- **acceptance-gate**가 참조할 AC 체크박스
- 이후 모든 게이트의 판단 기준

### 2.3 계획

```
메인 에이전트가 구현 계획 수립
  → 복잡하면 OMC planner 활용 가능
  → 외부 정보 필요하면 researcher 호출 (Exa)
  → DB 스키마 확인 필요하면 db-worker 호출 (Supabase)
  
  이 단계에서는 Edit/Write를 안 하므로 게이트에 안 걸림
```

### 2.4 구현

```
메인 에이전트 또는 범용 Opus 서브에이전트가 코드 작성

파일을 편집하려면:
  1. 먼저 Read → read-tracker가 read-log.txt에 기록
  2. Edit/Write 시도
     → [PreToolUse] scope-gate: seed.yaml의 OUT OF SCOPE 확인
       → 범위 밖이면 차단 + 에러 메시지
     → [PreToolUse] context-gate: read-log.txt 확인
       → 미열람이면 차단 + "먼저 Read하세요"
     → 둘 다 통과하면 편집 실행

병렬 구현:
  → 독립적인 파일/모듈이면 Opus 서브에이전트 여러 개 동시 실행
  → 각 서브에이전트도 같은 hook chain을 탐 (같은 .omc/harness-state/ 공유)

MCP 필요 시:
  → DB 작업 → db-worker
  → 리팩터링 → refactorer  
  → 복합 작업 → full-context
```

### 2.5 검증

구현이 끝나면, 커밋 전에 검증 단계를 거침.

```
1. 빌드/테스트 실행
   → npm test, npm run build 등
   → [PostToolUse] backpressure-tracker가 성공 기록
     → backpressure-status = "PASS"
     → test-history.json에 추가

2. reviewer 호출 (코드 변경 ≥10줄 or 로직 변경)
   → Pass 1: reviewer 자체 분석 (Opus)
   → Pass 2: codex review --uncommitted (GPT-5.4)
   → Pass 3: Agent(oh-my-claudecode:code-reviewer) (별도 Opus)
   → 3개 결과 교차 검증
   → docs/reviews/review-YYYY-MM-DD-HHMMSS.md 기록
   → Verdict: PASS / PASS WITH NOTES / FAIL

3. verifier 호출 (AC 있을 때 필수)
   → seed.yaml AC 항목별 증거 확인
   → 하네스 게이트 상태 확인
   → 빌드/테스트 직접 재실행
   → scope 이탈 여부 확인
   → Verdict: PASS / FAIL / INCOMPLETE
```

### 2.6 커밋

```
git commit 시도
  → [PreToolUse: Bash] 3개 게이트 순차 실행:

  1. acceptance-gate
     → seed.yaml AC 체크박스 확인
     → 미완료 [ ] 있으면 → 차단
     → acceptance-done 플래그 있으면 → 통과

  2. backpressure-gate (위험도 인식)
     → risk-assess.mjs로 변경 유형 판단
     → low (문서만) → 통과
     → medium (코드) + 상태 없음 → 경고
     → high/critical + PASS 아님 → 차단
     → backpressure-skip 플래그 있으면 → 통과

  3. review-gate (위험도 인식)
     → risk-assess.mjs로 변경 유형 판단
     → low → 통과
     → medium + 리뷰 없음 → 경고
     → high/critical + 리뷰 없음 → 차단
     → 리뷰 FAIL → 차단
     → review-skip 플래그 있으면 → 통과

  전부 통과하면 커밋 성공

  → [post-commit] harness-version-bump.sh
    → 하네스 파일이 변경됐으면 버전 범프 + 태그 생성
```

### 2.7 완료 보고

```
메인 에이전트가 사용자에게 보고:
  → Applied rules
  → Evidence (파일 경로, 커맨드 출력)
  → Verification (reviewer/verifier 결과 참조)
```

## 3. 위험도별 게이트 동작 요약

```mermaid
flowchart LR
    subgraph risk["변경 위험도 판정 (risk-assess.mjs)"]
        R1["low<br/>문서·설정만"]
        R2["medium<br/>코드 변경"]
        R3["high<br/>코드 100줄+"]
        R4["critical<br/>auth·migration·secrets"]
    end

    subgraph gates["게이트 반응"]
        G1["backpressure: 통과<br/>review: 통과"]
        G2["backpressure: 경고<br/>review: 경고"]
        G3["backpressure: 차단<br/>review: 차단"]
        G4["backpressure: 차단<br/>review: 차단"]
    end

    subgraph override["오버라이드"]
        O1["불필요"]
        O2["불필요"]
        O3["backpressure-skip<br/>review-skip"]
        O4["backpressure-skip<br/>review-skip<br/>⚠️ 사용자 확인 필수"]
    end

    R1 --> G1 --> O1
    R2 --> G2 --> O2
    R3 --> G3 --> O3
    R4 --> G4 --> O4

    style R1 fill:#006400,color:#fff
    style R2 fill:#8b6914,color:#fff
    style R3 fill:#8b4000,color:#fff
    style R4 fill:#8b0000,color:#fff
```

## 4. 서브에이전트 호출 타이밍

```mermaid
sequenceDiagram
    participant U as 사용자
    participant M as 메인 에이전트
    participant R as researcher
    participant DB as db-worker
    participant RF as refactorer
    participant RV as reviewer
    participant VF as verifier
    participant OE as Opus (범용)

    U->>M: "결제 기능 만들어줘"
    Note over M: 킥오프 → seed.yaml 생성

    M->>R: "Stripe API 최신 스펙 확인"
    R-->>M: Stripe v2024.12 webhook 스펙 + 문서 URL

    M->>DB: "payments 테이블 스키마 확인"
    DB-->>M: 현재 스키마 + RLS 정책

    Note over M: 계획 수립 완료

    par 병렬 구현
        M->>OE: "webhook handler 구현"
        M->>OE: "결제 상태 enum 추가"
        M->>DB: "payments 테이블 migration 생성"
    end
    OE-->>M: handler 완료
    OE-->>M: enum 완료
    DB-->>M: migration SQL

    Note over M: 구현 완료 → 검증 단계

    M->>M: npm test, npm run build

    M->>RV: "변경사항 리뷰"
    Note over RV: Pass 1: 자체 분석
    Note over RV: Pass 2: codex review
    Note over RV: Pass 3: OMC code-reviewer
    RV-->>M: PASS WITH NOTES (docs/reviews/에 기록)

    M->>VF: "AC 검증"
    VF-->>M: PASS (4/4 AC 충족)

    M->>M: git commit
    Note over M: acceptance-gate ✅
    Note over M: backpressure-gate ✅
    Note over M: review-gate ✅

    M->>U: "완료. 리뷰 결과, 검증 결과 첨부."
```
