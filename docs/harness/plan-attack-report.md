# Plan-Attack Report (task_id: 20260526-164034-85c0)

**date**: 2026-05-26
**run_count**: 1
**result (raw critic)**: BLOCK
**effective policy gate**: WARN — 첫 번째 plan-attack은 WARN으로 처리(정책: `rules/adversarial_review.md`). 사용자가 발견 사항 검토 후 진행/보강을 결정.

## (a) Goal 달성 불가능 사유

1. **[CRITICAL] Claude 웹/데스크톱 export 포맷이 v0 차단 요인**
   - 증거: assumptions `"Claude 웹/데스크톱 채팅은 사용자가 export할 수 있는 경로가 있다"`, risks `"export 포맷 비공식/변경 가능"`
   - 근거: Anthropic 공식 bulk-export는 사용자 데이터 요청 JSON뿐이며 스키마 보장 없음. AC1이 "양쪽 모두 import"를 요구하므로 포맷 미확정 시 AC 통과 불가.
   - 제안: startdev 전에 실제 export 샘플 1건 확보 → 스키마 픽스 후 진행. 미확보 시 AC1을 "Code 세션 우선, 채팅은 best-effort"로 축소.

2. **[HIGH] "시간적으로 가까운 다른 영역 세션 후보" 정의 부재**
   - 증거: AC `"시간적으로 가까운 다른 영역(학습/작업) 세션 후보가 함께 표시"`
   - 근거: "가까운"의 윈도(±1h? ±1d?)와 "영역" 라벨링 규칙(파일 경로? import 소스?) 미정의. 구현자 2명이 다르게 해석 가능.
   - 제안: 시간 윈도 파라미터화 + 영역 = import source(code/chat) 명시.

3. **[HIGH] 기술스택 미결정과 AC 비용 폭발의 충돌**
   - 증거: constraints `"기술 스택은 startdev 단계에서 결정"` + risks `"임베딩 비용·시간 폭발"`
   - 근거: 임베딩 모델 선택(API vs 로컬)이 비용/지연/오프라인 동작/AC8 자동테스트 환경을 좌우. 미결정 상태로는 AC8 "E2E 1개 통과" 검증 가능 여부 자체가 불확정.

## (b) AC 불충분 지점

- **[CRITICAL] 성공 임계값 부재**: AC3 `"시맨틱 매치 결과 반환"`은 결과가 1건이든 무관히 통과. recall@k, 최소 검색 지연, 0-hit 처리 명시 없음.
- **[HIGH] AC8 E2E "최소 1개"가 회귀 방지 불충분**: import→embed→search 한 경로만 테스트. 중복 import(risks에 명시)·실패 재시도·대용량 세션 케이스 없음.
- **[MEDIUM] AC4 "전후 컨텍스트"의 단위 미정**: 청크 ±N? 세션 전체? UI 페이지네이션? 측정 불가.
- **[MEDIUM] AC7 mesh 접속 검증이 risks `"mesh 미설치 시 검증 불가"`와 모순**: fallback 검증 경로 부재.

## (c) Scope 누락 치명적 항목

- **[CRITICAL] 로컬 저장 데이터 보호 정책 부재**: constraints는 "로컬에만 저장"만 명시. 디스크 암호화/백업/도난 시나리오 무기재. Claude 세션엔 API key·secret이 포함될 수 있어 평문 저장 시 데이터 유출 위험.
- **[HIGH] 중복/재import 정책 부재**: risks에 `"중복 import dedup 누락"` 명시되어 있으나 AC·constraints 어디에도 dedup 키(세션 ID? content hash?) 정의 없음.
- **[HIGH] 스키마 마이그레이션 경로 부재**: v0 raw 보존이라 했으나 청킹·메타 스키마 변경 시 재인덱싱 비용을 누가 부담하는지 미정. 그린필드라도 1주 내 재처리 발생 가능.
- **[MEDIUM] 관찰가능성 부재**: 임베딩 실패율·검색 지연 로깅 기준 없음. risks `"API 실패 처리 누락"`이 운영 단계에서 사일런트 실패로 이어짐.

## 종합 판정 (critic 원본)
- result: BLOCK
- 핵심 메시지: Claude 채팅 export 스키마 미확정(CRITICAL)과 raw 로그 내 비밀정보 보호 누락(CRITICAL) 2건이 startdev 진입 차단. 임베딩 스택·dedup·AC 임계값을 확정한 v0.1 seed로 revise 필요.

## 정책 처리 결과 (run_count=1)
- **gate result: WARN** — 사용자에게 결과 표시 후 결정 위임
- **권장 액션**:
  - 사용자가 진행을 선택 시 → seed 보강 없이도 startdev 진입 가능 (단, 보강 권장)
  - 사용자가 보강 선택 시 → 아래 권장 보강 항목 반영 후 run_count=2로 재평가. 그 시점에 CRITICAL이 남아 있으면 BLOCK 처리됨.

## 권장 보강 (사용자 검토)

### 즉시 반영 권장 (2 CRITICAL 해소)
1. **Claude 채팅 export 사전 확보**
   - startdev 진입 전에 본인 계정의 Claude 웹/데스크톱 export를 실제로 한 번 받아보고 스키마 픽스.
   - 안 되면 AC1을 "Code 세션 우선, 채팅은 best-effort(받을 수 있는 형식 한해서)"로 명시적 축소.
2. **데이터 보호 정책 명시**
   - MUST에 추가 후보: "raw 저장 시 API key/secret 패턴 마스킹 또는 별도 secrets vault" / "DB 파일은 OS 디스크 암호화 위에 배치(예: LUKS/FileVault)" / "백업 권고(주 1회 스냅샷)" 중 택일·복수.

### v0.1 보강 권장 (CRITICAL 외 HIGH 다수 해소)
- AC 임계값 명시: recall@5 ≥ N%, 검색 지연 < N초, 0-hit 시 UX 안내 명시
- dedup 키 정의 (세션 ID 또는 content hash)
- "약한 연결" 시간 윈도 파라미터 + 영역 라벨 정의
- 스키마 마이그레이션 전략 1줄 (재인덱싱 스크립트 보유 등)
- 관찰가능성 최소셋 (임베딩 실패 카운터, 검색 지연 히스토그램)

### v1으로 미루기 가능 (HIGH/MEDIUM 중 일부)
- 대용량 세션 E2E 테스트
- 정량 회귀 방지 테스트
- mesh 접속 fallback 검증 경로
