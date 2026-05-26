# MCP Server Policies

This document defines when and how to use MCP (Model Context Protocol) servers.

## Priority Order

When multiple tools can accomplish the same task:

1. **MCP tools** (specialized, maintained) over generic alternatives
2. **Symbolic tools** (Serena with `--context claude-code`) over text-based file operations
3. **Cached/indexed sources** (Context7) over live web search

---

## LSP Layering (Code Navigation & Symbols)

**Purpose**: 네 개의 독립 LSP 레이어가 공존할 때 어느 레이어를 언제 쓰는지 규정한다.

### 4 Layers

| Layer | What | Model-visible? | 활성 조건 |
|---|---|---|---|
| **A. Claude Code native LSP** | Claude Code 본체(v2.0.74+)가 내부적으로 쓰는 심볼 룩업/진단(~50ms) | ✗ (툴 비노출) | 자동 — 설치된 언어 서버를 런타임이 인식 |
| **B. Official plugins** (e.g. `typescript-lsp`) | 레이어 A에 언어 서버 바이너리를 바인딩하는 Claude 공식 플러그인 | ✗ (A 경유) | 플러그인 설치 + 전역 바이너리 설치 (예: `npm i -g typescript-language-server typescript`) |
| **C. OMC MCP LSP** (`mcp__plugin_oh-my-claudecode_t__lsp_*`) | 모델이 직접 호출하는 LSP 원시 API (hover, goto_definition, find_references, diagnostics, diagnostics_directory, document_symbols, workspace_symbols, rename, prepare_rename, code_actions, code_action_resolve, servers) | ✓ | 언어 서버 바이너리가 PATH에 있을 때 자동 스폰 |
| **D. Serena MCP** (`mcp__serena__*`) | 심볼 단위 **의미 편집** (replace_symbol_body, insert_before/after_symbol, safe_delete_symbol, rename_symbol) + name-path 트리 | ✓ | `--context claude-code` 필수 |

### Call-priority ordering

1. **편집기 내부 룩업·진단(투명)** → 레이어 A 자동. 모델이 호출할 일 없음.
2. **단순 LSP 원시 질의** (hover / goto_definition / find_references / code_actions) → 레이어 C
3. **프로젝트 전역 진단** → 레이어 C의 `lsp_diagnostics_directory`
4. **심볼 바디 치환·삽입·삭제, 의미 단위 refactor** → 레이어 D (C에는 이 기능 없음)
5. **새 파일 숙지** → 레이어 D의 `get_symbols_overview` → `find_symbol` 흐름 우선

### Completion evidence (복원)

완료 주장 시 최소 하나의 LSP 기반 증거를 포함한다:
- "Implemented" → `lsp_diagnostics` 또는 `lsp_diagnostics_directory` 결과 clean
- "Refactored" → 영향 심볼에 대한 `lsp_find_references` 결과 일관됨
- "Fixed" → 재현 테스트 pass + 변경 파일 진단 0건

(근거: `claudedocs/CLAUDE_original.md:355`에서 회귀된 증거 요건을 현행 규칙으로 복원)

### Overlap suppression

- Serena는 **MUST** `--context claude-code`로 구동 (OMC LSP와 겹치는 hover/goto 비활성 → 토큰·429 리스크 감소).
- `typescript-lsp` 공식 플러그인(B)과 OMC LSP(C)가 같은 TS 서버를 각각 별도 프로세스로 띄울 수 있음. 메모리 중복은 의도적 허용, 기능 충돌 없음.

### Language-server absence fallback

필요한 언어 서버 바이너리가 PATH에 없어 레이어 B·C가 비활성일 때:
- 모델 호출 가능한 원시 LSP 기능은 부재 → 레이어 D(Serena) + `Grep`/`Read`로 전환
- 진단: `mcp__plugin_oh-my-claudecode_t__lsp_servers`로 설치 상태 일괄 조회
- 복구: 해당 언어 서버 전역 설치 (예: `npm i -g typescript-language-server typescript`)

### Grep vs LSP 판단 로직

**원칙**: 질의가 **구조적**(심볼·타입·참조)인가 **문자열 기반**(리터럴·패턴)인가를 먼저 분류한다.

| 질의 유형 | 우선 툴 |
|---|---|
| 심볼 정의·참조·타입·진단 | **MUST** 레이어 C (`lsp_goto_definition`, `lsp_find_references`, `lsp_diagnostics`) |
| 심볼 단위 편집 (바디 치환·삽입·삭제) | **MUST** 레이어 D (Serena) — C에 해당 기능 없음 |
| 새 파일 또는 >500줄 파일의 구조 파악 | **SHOULD** 레이어 D `get_symbols_overview` |
| 문자열·주석·에러 메시지·환경변수·설정값 | **MUST** `Grep` |
| 파일·디렉토리 이름 패턴 | **MUST** `Glob` |
| 심볼명 모름 (의도 기반 탐색, 코드베이스 <100파일 또는 키워드 확정적) | **SHOULD** `Grep`에 관련 키워드 복수(OR)로 후보 추림 → 레이어 C로 정밀화 |
| **콜드스타트 + 의도 기반 (코드베이스 >500파일, CLAUDE.md/AGENTS.md로 미해결)** | **SHOULD** `grepai search` Top-5 → 레이어 C로 정밀화 (trial) |
| **유저가 "grepai"·"의미 기반 검색"을 명시** | **MUST** `grepai search` 경유 |
| 동적 디스패치·설정 주도·폴리글롯 코드의 call 추적 | **MAY** `grepai trace callers/callees` — 단일언어 정적코드는 `lsp_find_references` 우선 |

**MUST NOT**:
- LSP 가용 상태에서 심볼 참조를 `Grep` 단독으로 결론 (주석·유사 식별자 오탐 위험)
- 파일 전체 `Read` 후 눈으로 심볼 탐색 — `lsp_document_symbols` 또는 `get_symbols_overview` 선행
- 심볼명·파일경로·리터럴이 유저 프롬프트에 이미 주어졌는데 `grepai` 호출 (LSP/Grep 직행)
- `grepai` 랭킹만으로 작업 결론 — 상위 1–2개를 LSP/Read로 검증해야 함

**MAY skip LSP** when:
- 수정 위치가 이미 정확히 특정된 단일 라인 편집
- 비코드 파일(md / yaml / json) — Grep·Read로 충분

**비고 — 시맨틱 검색 레이어 (grepai, 2주 시범)**:
CLI + Skill 래퍼 경로로 도입(MCP 서버 아님 → context tax 0). 상세 라우팅은 `.claude/skills/grepai-search/SKILL.md`. 종료 조건: (a) 일 평균 <1회 호출 또는 (b) 오도 사례 > 유도 사례 → skill 디렉토리 삭제로 롤백. 배경: `docs/sum/session_2026-04-21_grepai-adoption-decision.md`.

---

## Context7 (Library Documentation)

**Purpose**: Retrieve up-to-date documentation and code examples for libraries/frameworks.

### MUST use when:
- Introducing **new** external APIs, SDKs, or dependencies
- Using version-sensitive syntax or features
- Suspected deprecations or breaking changes
- Unfamiliar library patterns

### MAY skip when:
- In-repo code already demonstrates the same API usage pattern
- Well-known, stable APIs (e.g., `JSON.parse`, `Array.map`)

### Workflow:
1. Call `resolve-library-id` first to get the library ID
2. Then call `query-docs` with specific questions
3. Limit to 3 calls per question

---

## Serena (Symbolic Code Analysis)

**Purpose**: LSP-based code navigation, refactoring, and symbolic editing.

### SHOULD use when:
- Finding symbol definitions and references (`find_symbol`, `find_referencing_symbols`)
- Understanding call hierarchy and dependencies
- Refactoring (rename, extract, move)
- Getting file/symbol overview (`get_symbols_overview`)
- `replace_symbol_body` / `insert_before_symbol` — 심볼 단위 편집이 필요할 때

### MAY skip when:
- Simple single-line edits where exact location is known
- Non-code files (markdown, config, etc.)
- OMC LSP tools로 충분한 단순 탐색 (goto definition, find references)

### Best Practices:
- **MUST** run with `--context claude-code` flag to disable tools that overlap with OMC LSP (reduces token cost and 429 risk)
- Use `get_symbols_overview` before diving into a new file
- Prefer `find_symbol` with `include_body=True` over reading entire files
- Use `replace_symbol_body` for function/method replacements
- Use `replace_content` with regex for targeted line edits

---

## Supabase (Database Management)

**Purpose**: Manage Supabase projects, execute SQL, apply migrations.

### MUST use migrations (`apply_migration`) for:
- Schema changes (CREATE, ALTER, DROP)
- Index creation/modification
- RLS policy changes

### MAY use direct SQL (`execute_sql`) for:
- Data queries (SELECT)
- Debugging and inspection
- One-off data fixes (with caution)

### Best Practices:
- Always check `get_advisors` for security/performance issues after DDL changes
- Use `generate_typescript_types` after schema changes
- Prefer branches for experimental changes

---

## Web Search (Exa / web-search)

**Purpose**: Search the web for current information, error solutions, latest docs.

### SHOULD use when:
- Current events or recent releases (post knowledge cutoff)
- Error messages not found in repo or Context7
- Comparing multiple solutions/approaches
- Finding community discussions or GitHub issues

### MAY skip when:
- Information is available in repo or offline knowledge
- Context7 has the documentation needed
- Question is about stable, well-documented features

---

## Browser Tools (browser-tools-mcp)

**Purpose**: Browser automation, screenshots, DOM inspection.

### SHOULD use when:
- E2E testing requiring visual verification
- Capturing screenshots for documentation
- Debugging frontend rendering issues
- Inspecting live DOM state

### Caution:
- Requires browser extension running
- May not work in headless environments

---

## Exa (AI Search)

**Purpose**: AI-powered semantic search with better relevance than keyword search.

### SHOULD use when:
- Complex, nuanced queries
- Finding conceptually similar content
- Research requiring synthesis

### MAY skip when:
- Simple keyword searches suffice
- Exact phrase matching needed

---

## React Design Systems (react-design-systems)

**Purpose**: Access design system components and patterns.

### SHOULD use when:
- Building UI components
- Looking for design tokens/variables
- Checking component APIs and props

### Note:
- Requires local server running at `http://10.39.60.65:3010`

---

## Stitch (Proxy)

**Purpose**: MCP proxy/aggregator.

### Usage:
- Transparent proxy layer
- No direct policy needed

---

## General Guidelines

1. **Check availability first**: Not all MCP servers may be running
2. **Prefer specialized tools**: Use the right tool for the job
3. **Cache awareness**: Some tools cache results; re-query if data may be stale
4. **Error handling**: If MCP tool fails, fall back to alternative methods
5. **Rate limits**: Some hosted services have rate limits; batch queries when possible
