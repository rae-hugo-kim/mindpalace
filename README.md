**[English](README.en.md)**

# mindpalace

과거 학습/작업 기록(Claude Code 세션, Claude 웹·데스크톱 채팅)을 어렴풋한 단서로도 다시 찾아 쓸 수 있게 하는 개인 지식저장창고. 시맨틱 검색 + 메타데이터 자동 추출 + 본인 기기에서 mesh로 접근 가능한 로컬 웹 UI.

## 목표

Claude Code 세션 로그와 Claude 웹/데스크톱 채팅 세션을 수동 import해 raw로 보존하고, 파일 path/명령/도구/시간/표제어 등 메타데이터를 자동 추출하며, 자연어 쿼리로 시맨틱 검색하여 청크 매치 + 세션 컨텍스트로 결과를 계층적으로 표시하는 개인 지식저장창고를 로컬 호스팅 + Tailscale/VPN mesh 접근 가능한 웹 UI로 v0 구축한다.

## 수락 기준

- [ ] Claude Code + 채팅 export 양 소스 import → DB에 raw 보존
- [ ] 메타데이터 자동 추출 (Code: 파일 path/명령/도구/에러, 채팅: 시간/표제어)
- [ ] 자연어 시맨틱 검색이 청크 단위로 매치 결과 반환
- [ ] 결과 표시가 청크 hit + 세션 컨텍스트 계층
- [ ] 시간/파일/도메인 메타 필터 작동
- [ ] 시간·표제어 기반 약한 학습-작업 연결 후보 표시
- [ ] Tailscale mesh 내 다른 기기에서 웹 UI 접속 가능
- [ ] 핵심 경로 end-to-end 자동 테스트 1개 이상 통과

## 제약

- 자동 인입(gmail/Claude API 자동 sync)은 v1 이후
- ingest 시점 무거운 가공 금지 (학습 수준 굳어버림 방지)
- 데이터는 로컬에만 — 클라우드 저장 금지
- 공개 URL/외부 인증 없음 — 접근은 Tailscale/VPN mesh 한정
- 다중 사용자 미지원 (1인 도구)

## 상태

🚧 개발 중 — 자세한 컨텍스트는 [`docs/harness/kickoff-summary.md`](docs/harness/kickoff-summary.md) 참고.
