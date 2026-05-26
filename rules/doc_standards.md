# Documentation Standards

저작 매체는 마크다운(SST). HTML은 *파생* 산출물 또는 *1회성* 사람용 아티팩트에만
허용한다. 본 표준은 마크다운 저작 품질을 끌어올려 [`docs-build.sh`](../scripts/docs-build.sh)가
빌드하는 mdBook 뷰어에서 가시성을 유지하도록 한다.

## Rules

### R1. 다이어그램은 Mermaid 기본, ASCII는 코드 코멘트 한정

- 문서 본문의 다이어그램은 ```` ```mermaid ```` 코드펜스를 사용.
- ASCII 다이어그램은 **코드 코멘트 안 5–10줄 짧은 흐름**에 한해 허용.
- ASCII 아트로 그린 그래프·플로우차트를 문서 본문에 두지 않는다.
- 빌드 시점 검증: `scripts/docs-build.sh`가 mmdc로 syntax 오류를 잡아 빌드 실패시킴.

### R2. 긴 문서(대략 200줄+)는 상단 요약 강제

- 200줄을 넘어가는 문서는 **TL;DR** 또는 **요약 (200자 내외)** 섹션을 상단에 둔다.
- 200줄은 hard cap이 아닌 trigger threshold. 가능하면 400줄 이전에 분할.
- 요약은 결정사항·결론을 담고, 본문은 근거·논거·구체적 데이터를 담는다.

### R3. GFM 표 정렬

- 표는 GitHub Flavored Markdown 형식 (`|---|---|`) 사용.
- `prettier --parser markdown` 또는 IDE 자동 포맷터로 정렬 유지.
- raw 마크다운에서 보더라도 컬럼이 어긋나지 않게 둔다.

### R4. 사람용 1회성 HTML은 `artifacts/`로

- 1회성 explainer·mockup·design preview·PR 시각화 등은 `artifacts/` 트리에 둔다.
- `docs/` 안에 HTML 파일을 두지 않는다 (mdBook 뷰어에 포함되지 않고 SST 오염).
- 상세는 [`artifacts/README.md`](../artifacts/README.md) 참조.

### R5. 스킬 정의 파일은 대문자 `SKILL.md`

- 스킬 디렉터리의 entry 파일은 반드시 `SKILL.md` (대문자 S, K, I, L, L, M, D).
- 소문자 `skill.md`는 Linux 환경에서 silent failure
  ([anthropics/skills#314](https://github.com/anthropics/skills/issues/314)).
- 글로벌(`~/.claude/skills/`)·로컬(`.claude/skills/`) 양쪽 모두 동일.

## Build & View

- 빌드: `bash scripts/docs-build.sh` → `book/`에 정적 사이트 생성
- 로컬 hot reload: `mdbook serve` → http://localhost:3000
- 빌드 산출물(`book/`), mermaid 런타임 JS(`mermaid.min.js`, `mermaid-init.js`)는 gitignore

## Related

- `docs/harness/seed.yaml` AC2 — 본 표준의 정의 원본
- `rules/change_control.md` — 최소 변경 원칙 (본 표준의 over-prescription 방지)
- `artifacts/README.md` — 1회성 HTML 산출물 정책
