# Kickoff Summary — Agent-First Docs Pipeline

## Goal

Markdown을 single source of truth로 유지하면서, 사람이 읽기 좋은 HTML 뷰어
(mdBook)와 1회성 HTML 산출물 격리 위치(`artifacts/`)를 함께 갖춘 에이전트
우선 문서 파이프라인을 도입한다. HTML을 입력(SST)으로 쓰는 방향은 명시적으로
차단한다.

## Context

- 발단: Thariq Shihipar의 "HTML is the new markdown" 주장
  ([원문](https://claude.com/blog/using-claude-code-the-unreasonable-effectiveness-of-html))을
  우리 하네스에 어떻게 받을지 검토.
- 결론: HTML 저작 채택은 입력(룰·스킬·정책) 영역에서 부적합. 출력 영역에서도
  mdBook으로 MD→HTML 빌드하는 패턴이 토큰·diff·grep·옵션 가치 모두에서 우월.
- 두 차례 외부 리서치 보고서 검토 후에도 결론 변동 없음. 두 가지 일반 refinement만
  반영: `assets/` 토큰 거동, `SKILL.md` 대소문자.
- 상세: [`docs/brainstorming/html-vs-markdown-artifacts.md`](../brainstorming/html-vs-markdown-artifacts.md)

## Constraints

- 정책/스킬은 마크다운 유지 (LLM 입력 컨텍스트 토큰 효율, grep/diff 친화성).
- 도입 도구는 단일 바이너리·최소 의존성 우선 (mdBook이 이 기준).
- 기존 파일 일괄 마이그레이션 금지 (over-engineering 회피).
- 하네스 규칙 준수 우선: `rules/change_control.md` (최소 변경),
  `rules/anti_hallucination.md` (추측 도입 금지).

## Acceptance Criteria

상세는 `docs/harness/seed.yaml`. 항목만 요약:

- [ ] **AC1** — mdBook viewer 도입 (book.toml, mdbook-mermaid, scripts/docs-build.sh, bootstrap 도구 자동 설치, build script self-check)
- [ ] **AC2** — `rules/doc_standards.md` 신설 (5개 규칙)
- [ ] **AC3** — `.claude/skills/design-mockup/` 스킬 신설 (글로벌·로컬 sync)
- [ ] **AC4** — `artifacts/` 디렉터리 + gitignore 정책
- [ ] **AC5** — `preview/` 트랙 명시적 보류 결정 기록

## Out of Scope

- 기존 MD 파일 일괄 마이그레이션
- HTML 기반 SST 어느 위치에서든
- Storybook / shadcn / Next dev 환경 셋업 (Stage 3, 별 결정)
- D2 / PlantUML 등 Mermaid 대체 다이어그램 툴
- mdBook 외 SSG (Quarto, Hugo 등) 검토
- CI 자동 배포 (GitHub Pages 등)
- motion-design 스킬 트랙 (별도 백로그, brainstorming에 메모)
- 커뮤니티 스킬 fork/설치 (별도 결정)

## Assumptions

- Opus 4.7 1M 컨텍스트 사용 중이나 토큰 효율은 여전히 중요 (반복 호출 누적).
- 사용자의 문서 소비 surface는 IDE + 브라우저 둘 다. mdBook `serve`로 충분.
- `artifacts/`는 사람이 한 번 보고 버리는 산출물 격리용. 영속 유지가 필요한 결과는
  `docs/` 안 MD로 승격.

## Risks

- **R1**: mdbook-mermaid가 Mermaid validation을 강제하지 않을 가능성. →
  별도 validation step 또는 mdbook-mermaid-mmdr 검토.
- **R2**: 글로벌(`~/.claude/skills/`) ↔ 로컬(`.claude/skills/`) sync 누락. →
  PR 체크리스트에 명시.
- **R3**: 기존 placeholder 문서들이 새 표준과 불일치. →
  opportunistic 정리, 즉시 마이그레이션 안 함.

## Decisions

| 항목 | 값 | 이유 |
|------|-----|------|
| Viewer 출력 디렉터리 | `book/` (gitignore) | mdBook 도구 컨벤션, 호환성 유리 |
| 빌드 진입점 | `scripts/docs-build.sh` | 기존 `scripts/` 폴더 존재, 의존성 0 |
| design-mockup 산출 위치 | `artifacts/design/` (gitignore) | 파일 탐색기에서 즉시 접근, AC4 정책 통합 |
| PR 단위 | 단일 PR | AC 간 cross-reference 강함, review 비용 작음 |

## References

- `docs/harness/seed.yaml` — 구조화 명세
- `docs/brainstorming/html-vs-markdown-artifacts.md` — 의사결정 기록
- `rules/agent_routing.md`, `rules/change_control.md`, `rules/anti_hallucination.md` — 준수 대상 하네스 규칙
