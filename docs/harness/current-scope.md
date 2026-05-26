# Current Scope: 지식저장창고 (mindpalace) v0

**Created**: 2026-05-26
**Revision**: v0.1 (plan-attack 보강 반영)
**task_id**: 20260526-164034-85c0
**Authoritative source**: `docs/harness/seed.yaml` (this file is a derivative for hook compatibility)

## MUST
- Claude Code 세션 로그 수동 import (raw 보존)
- Claude 웹/데스크톱 채팅 수동 import (export 파일 수용 — 스키마는 사용자 샘플 확보 후 확정)
- import 직전 secret 패턴 마스킹 (API key/JWT/토큰 등) — raw에 평문 secret 남기지 않음
- DB 파일은 OS 디스크 암호화 볼륨 위에 배치 (비암호화 시 경고/차단)
- 시맨틱 검색 (임베딩 + 벡터 인덱스, 청크 단위)
- 메타데이터 자동 추출 (Code: 파일 path/명령/도구/에러, 채팅: 시간/표제어)
- 검색 결과 계층 표시 (청크 hit + 청크 ±3 컨텍스트 + 세션 컨텍스트)
- ±3일 윈도 + 표제어 기반 학습↔작업 약한 연결 후보 표시
- 웹 UI (로컬 서버) — 검색/import/결과 표시
- 로컬 데이터 보관 (DB 로컬)
- Tailscale/VPN mesh 통한 본인 기기 접근 가능
- raw immutable 보존 + 임베딩/메타는 derived data로 분리 (재인덱싱 스크립트 보유)
- dedup (세션 ID 우선, content hash 보조)
- 운영 로그 (import 결과, 임베딩 실패, 검색 지연)

## SHOULD
- 메타데이터 필터 UI (시간/파일/도메인)
- 인출 시점 LLM 즉석 요약 (lazy 가공)
- 학습-작업 자동 링크 카드 표시

## MUST NOT
- 자동 인입 (gmail/Claude API 자동 sync)
- ingest 시점 무거운 요약/개념 카드 자동 생성
- 클라우드 데이터 저장
- 공개 URL 노출 / 외부 인증
- 다중 사용자 지원
- raw 저장본에 평문 secret 남기기

## OUT OF SCOPE
- 삽질 방지 시스템 (GitHub 이슈/sum 영역)
- 일반 노트 통합 (회의록/책 메모)
- 협업/공유 기능
- 모바일 네이티브 앱 (모바일 브라우저 접근은 OK)
- 정량 검색 품질 지표 (recall@k 등) — v1
- 대용량 세션 회귀 테스트 — v1
- mesh 미설치 fallback — v1

## Acceptance Criteria
- [ ] Claude Code 세션 + 채팅 export 양 소스 import → DB에 raw 보존 (채팅 스키마는 샘플 확보 후 확정)
- [ ] 메타데이터 자동 추출 (Code: 구조물, 채팅: 시간/표제어)
- [ ] 자연어 시맨틱 검색이 청크 단위로 매치 결과 반환
- [ ] 결과 표시가 청크 + 컨텍스트(±3) 계층 (세션 단위 확장)
- [ ] 시간/파일/도메인 메타 필터 작동
- [ ] ±3일 시간·표제어 기반 약한 학습-작업 연결 후보 표시
- [ ] Tailscale mesh 내 다른 기기에서 웹 UI 접속 가능
- [ ] 핵심 경로(import → 마스킹 → 임베딩 → 검색) end-to-end 자동 테스트 1개 이상 통과
- [ ] Secret 패턴 마스킹 회귀 테스트 통과 (sk-..., JWT, password 등)
- [ ] 비암호화 볼륨 import 시 경고/차단 동작
- [ ] 검색 P95 응답 시간 ≤ 2초 (1만 청크 기준)
- [ ] 0-hit UX 안내 + 쿼리 완화 힌트
- [ ] dedup 회귀 테스트 통과 (재import 시 중복 없음)
- [ ] 운영 로그(import 결과/임베딩 실패/검색 지연) 기록
