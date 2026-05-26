## Kickoff Summary: 지식저장창고 (mindpalace) v0

**Date**: 2026-05-26
**Type**: New Project (mindpalace의 핵심 기능)

### JTBD
- **User**: 본인 (rae.kim) — 1인 사용자
- **Problem**: 과거 학습/작업 기록을 어렴풋한 단서로 다시 인출하지 못함. sum문서/이슈가 있어도 매칭이 안 되거나, "같은 현상 다른 원인"을 구분하지 못해 같은 삽질을 반복함. 인출 단서 자체가 fuzzy해서 정확 매칭이 안 됨.
- **Success**: 어렴풋한 단서(시간/주제/파일/명령 등)로 검색하면 시맨틱 + 메타데이터 기반 후보 묶음이 뜨고, 그 안에서 본인이 "그때 그거"를 발견해 다음 작업/학습에 활용할 수 있는 흐름이 작동.

### Context
- **Repo type**: 단일 레포 (mindpalace, 그린필드 + harness 인프라)
- **Tech stack**: 미정. 현재는 docs(mdBook) + bash 스크립트 + OMC/harness 통합. 애플리케이션 스택은 startdev 단계에서 선택.
- **Build cmd**: `scripts/docs-build.sh` (문서 빌드만, 애플리케이션 빌드 없음)
- **Test cmd**: `scripts/test-harness-audit.sh` (harness 자체 테스트, 애플리케이션 테스트 인프라 미정)
- **Existing patterns**: OMC harness, `docs/harness/audit.jsonl` 감사 로그, `seed.yaml` 컨트랙트, scope/acceptance/backpressure 게이트
- **Risks/constraints**:
  - 데이터 소스 추출 (Claude Code 세션 로컬 파일 위치/포맷, Claude 웹·데스크톱 export 까다로움)
  - 프라이버시 (개인 채팅 raw 저장 — 로컬로 한정)
  - 기술 선택 자유도가 큼 (스택 미정 상태)

### Scope

#### MUST
- Claude Code 세션 로그 수동 import (raw 보존)
- Claude 웹/데스크톱 채팅 수동 import (export 파일 수용)
- 시맨틱 검색 (임베딩 + 벡터 인덱스)
- 메타데이터 자동 추출 — Code: 파일 path/명령/도구/에러, 채팅: 시간/표제어
- 검색 결과 계층 표시 (청크 hit + 세션 컨텍스트 확장)
- 시간 + 표제어 기반 학습↔작업 약한 연결 후보 표시
- 웹 UI (로컬 서버) — 검색/import/결과 표시
- 로컬 데이터 보관 (DB 로컬)
- Tailscale/VPN mesh 통한 본인 기기 접근 가능 (앱: `0.0.0.0` 바인딩 / mesh 설정은 OS 외부 작업)

#### SHOULD
- 메타데이터 필터 UI (시간/파일/도메인)
- 인출 시점 LLM 즉석 요약 (가공의 lazy 모드)
- 학습-작업 자동 링크 카드 표시

#### MUST NOT
- 자동 인입 (gmail 자동 sync, Claude API 자동 끌어오기) — v1 이후
- ingest 시점 무거운 요약/개념 카드 자동 생성 (학습 수준에 굳어버림 위험)
- 클라우드 데이터 저장
- 공개 URL 노출 / 외부 인증 시스템
- 다중 사용자 지원

#### OUT OF SCOPE
- 삽질 방지 시스템 (GitHub 이슈/sum 영역으로 분리)
- 일반 노트 통합 (회의록/책 메모 등)
- 협업/공유 기능
- 모바일 네이티브 앱 (모바일 브라우저로 웹 UI 접근은 허용)

### Acceptance Criteria
1. Claude Code 세션 파일 + Claude 웹/데스크톱 export 파일 모두 수동 import 후 DB에 raw 보존된다
2. Code 세션 import 시 등장 파일 path/명령/도구/에러가 인덱싱되고, 채팅 import 시 시간/표제어가 인덱싱된다
3. 자연어 쿼리로 청크 단위 시맨틱 매치 결과가 반환된다
4. 검색 hit 청크 + 해당 세션 전후 컨텍스트를 같이 표시할 수 있다
5. 시간 범위, 파일 path, 도메인 등 메타데이터로 결과 좁히기 필터가 작동한다
6. 검색 결과에 시간적으로 가까운 다른 영역(학습/작업) 세션 후보가 함께 표시된다
7. 본인의 다른 기기에서 Tailscale mesh 내 IP를 통해 웹 UI 접속해 검색·결과 확인이 가능하다
8. 핵심 경로(import → 임베딩 → 검색) end-to-end 자동 테스트가 최소 1개 통과한다

### Edge Cases
- 큰 세션 (수만 토큰 Claude Code 세션) → turn 단위 청킹 전략
- 검색 결과 0건 → 빈 상태 안내 + 쿼리 완화 힌트
- 검색 결과 과다 (수백 건) → 시맨틱 점수 정렬 + 페이지네이션 / 메타 필터 권유
- 중복 import → 세션 ID/해시 기반 dedup

### Failure Modes
- 임베딩 API 호출 실패 → retry + 로깅, import는 raw만 저장하고 임베딩은 추후 재시도 큐
- DB 손상 → v0에선 수동 백업 권고 (스냅샷 디렉토리)
- export 파일 포맷 변경 → import 실패 시 명확한 에러 + raw 보존

### Backpressure
- **Verification method**: 핵심 경로(import → 임베딩 → 검색) end-to-end 자동 테스트 + 나머지 AC는 수동 체크리스트
- **How to run**: TBD — startdev에서 stack 선택 후 확정. 자동 테스트는 핵심 경로 최소 1개, 수동은 AC별 1줄 체크리스트로 정형화

---

### References
- 발산 캡처본: `docs/brainstorming/personal-knowledge-vault_2026-05-26_1509.md` (사고 흐름과 원칙 보존)
- seed (권위 있는 명세): `docs/harness/seed.yaml`
- scope (훅 호환): `docs/harness/current-scope.md`

---
Kickoff complete. Next: `/startdev`
