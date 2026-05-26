# Personal Harness Docs

이 문서 사이트는 본 repo의 `docs/` 트리를 mdBook으로 렌더링한 결과다.
저작 매체는 마크다운(SST)이며, 이 사이트는 *소비용* 파생 산출물이다.

## Navigation

좌측 사이드바에서 섹션별로 이동한다.

- **Architecture** — 하네스 구조와 워크플로 라이프사이클
- **Brainstorming** — 의사결정 기록, 구조 제안, 디자인 노트
- **Reviews** — 어드버서리얼 리뷰 보고서
- **Harness Outputs** — kickoff/seed/rubric 산출물
- **Internal Rules / Checklists** — `docs/rules`, `docs/checklists` 모듈
- **Session Summaries** — `docs/sum/` 회고 기록
- **Templates** — 문서 템플릿 모음

## 빌드

```bash
bash scripts/docs-build.sh   # 정적 사이트 빌드 → book/
mdbook serve                  # 로컬 hot reload, http://localhost:3000
```

**Fresh clone 주의**: `mermaid.min.js` / `mermaid-init.js`는 gitignore된 2.6MB
런타임 자산이라 처음에는 없음. **`bash scripts/docs-build.sh`를 먼저 한 번**
실행하면 자산이 자동 생성되고, 그 다음부터는 `mdbook serve` 직접 호출 OK.
빌드 스크립트를 건너뛰고 `mdbook serve`만 띄우면 Mermaid 다이어그램이
렌더되지 않음 (페이지 자체는 떠도 다이어그램만 빈 영역).

빌드 산출물(`book/`)은 gitignore. 호스팅은 별 결정 사항.

## 정책

- 저작은 마크다운으로 (`rules/doc_standards.md`)
- 1회성 사람용 HTML 산출물은 `artifacts/`로 (사이트에 포함되지 않음)
- 다이어그램은 Mermaid 기본
