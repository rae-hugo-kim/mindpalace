---
name: bootstrap
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(npm:*), Bash(npx:*), Bash(cargo:*), Bash(claude:*), Bash(omc:*), Bash(which:*), Bash(command:*), Bash(echo:*), Bash(cat:*), Bash(curl:*), Bash(pip:*), Bash(uvx:*), AskUserQuestion
argument-hint: [--skip-optional]
description: Bootstrap development environment with OMC, RTK, and MCP servers
---

# Bootstrap - Development Environment Setup

## Goal

이 하네스 템플릿을 사용하기 위한 개발 환경을 구축한다.
OMC + RTK 설치, 범용 MCP 서버 자동 등록, 선택적 MCP 서버 안내, docs viewer
빌드 도구(mdBook + Mermaid)까지 한 번에 처리.

## Non-Negotiables

| Rule | Violation = STOP |
|------|------------------|
| **Claude Code CLI 필수** | `claude` 명령어 없으면 안내 후 중단 |
| **npm/npx 필수** | Node.js 없으면 안내 후 중단 |
| **기존 설정 덮어쓰지 않음** | 이미 등록된 MCP 서버는 스킵 |

## Inputs

- `$ARGUMENTS`:
  - (없음) → 전체 플로우 실행
  - `"--skip-optional"` → 선택적 MCP 서버 질문 생략

## Workflow

### Phase 0: Preflight

```
1. claude --version 확인 → 실패 시 "Claude Code CLI를 먼저 설치하세요" 안내 후 중단
2. node --version, npm --version 확인 → 실패 시 "Node.js를 설치하세요" 안내 후 중단
3. 현재 설치 상태 수집:
   - which omc → 설치 여부
   - which rtk → 설치 여부
   - claude mcp list → 등록된 MCP 서버 목록
```

### Phase 1: OMC 설치 (자동)

```
1. omc가 이미 설치되어 있으면 → "✓ OMC already installed" 출력, 스킵
2. 미설치 시:
   npm install -g oh-my-claudecode
3. 설치 확인:
   omc --version
4. 초기 설정:
   omc setup
```

실패 시: 에러 메시지 그대로 출력, 수동 설치 안내 후 다음 단계로 진행.

### Phase 2: RTK 설치 (자동)

```
1. rtk가 이미 설치되어 있으면 → "✓ RTK already installed" 출력, 스킵
2. 미설치 시:
   cargo install rtk-cli
   (cargo 없으면 → "Rust/Cargo를 설치하세요: https://rustup.rs" 안내, 스킵)
3. 설치 확인:
   rtk --version
```

RTK는 선택적 — 설치 실패해도 중단하지 않고 계속 진행.

### Phase 3: Docs Build Tools (자동)

`scripts/docs-build.sh`와 `mdbook serve`가 의존하는 도구. 템플릿 fresh-clone
에서 docs viewer 즉시 동작을 위해 설치.

```
1. mdbook 체크:
   - command -v mdbook → 있으면 "✓ mdbook already installed" 스킵
   - 미설치 시: cargo install mdbook
   - cargo 없으면 → "Rust/Cargo를 설치하세요: https://rustup.rs" 안내, 스킵

2. mdbook-mermaid 체크:
   - command -v mdbook-mermaid → 있으면 스킵
   - 미설치 시: cargo install mdbook-mermaid

3. mmdc (mermaid-cli) 체크:
   - command -v mmdc → 있으면 스킵
   - 미설치 시: npm install -g @mermaid-js/mermaid-cli
```

셋 모두 선택적 — 설치 실패해도 중단하지 않고 계속 진행. docs viewer를
나중에 사용하지 않을 프로젝트는 그대로 두고 넘어가도 됨.

### Phase 4: 범용 MCP 서버 등록 (자동)

이미 등록된 서버는 스킵. 미등록 서버만 추가:

```bash
# context7 — 라이브러리/프레임워크 공식 문서 조회
claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp@latest

# serena — 시맨틱 코드 탐색/리팩토링 (--context claude-code로 OMC LSP 중복 제거)
claude mcp add --scope user serena -- uvx --from "git+https://github.com/oraios/serena" serena start-mcp-server --context claude-code

# exa — AI 웹 검색
claude mcp add --transport http --scope user exa https://mcp.exa.ai/mcp

# browser-tools-mcp — 브라우저 콘솔/네트워크/스크린샷
claude mcp add --scope user browser-tools-mcp -- npx -y @agentdeskai/browser-tools-mcp@1.2.0
```

각 서버 등록 후 성공/실패 표시.

### Phase 5: 선택적 MCP 서버 (인터랙티브)

`--skip-optional` 이면 이 단계 스킵.

AskUserQuestion으로 선택지 제시:

```
추가로 설치할 MCP 서버를 선택하세요 (쉼표로 구분, 엔터로 스킵):

1. supabase — Supabase DB/Edge Functions 관리
2. react-design-systems — React 컴포넌트 디자인 시스템 조회
3. pixelmaker — 픽셀 아트 생성/추출

예: 1,2 또는 all 또는 엔터(스킵)
```

선택된 서버 설치:

```bash
# supabase (SUPABASE_ACCESS_TOKEN 필요)
# → 토큰이 없으면 https://supabase.com/dashboard/account/tokens 안내
claude mcp add --scope user supabase -- npx -y @supabase/mcp-server-supabase@latest

# react-design-systems (로컬 서버 필요 — URL 입력받음)
# → AskUserQuestion으로 서버 URL 입력받기
claude mcp add --transport sse --scope user react-design-systems <url>

# pixelmaker (로컬 Python 패키지 필요)
# → 설치 경로 안내만 제공
```

### Phase 6: 결과 리포트

```markdown
## Bootstrap Complete

### Installed
- ✓ OMC vX.Y.Z
- ✓ RTK vX.Y.Z (또는 ✗ skipped)

### MCP Servers
| Server | Status |
|--------|--------|
| context7 | ✓ registered |
| serena | ✓ registered |
| exa | ✓ registered |
| browser-tools-mcp | ✓ registered |
| supabase | ✓ registered (또는 — skipped) |
| ... | ... |

### Next Steps
1. Claude Code를 재시작하면 MCP 서버가 활성화됩니다
2. `/init <project-name>` — 새 프로젝트 생성
3. `/kickoff` — 프로젝트 스코프 정의
```

## Error Handling

| Condition | Action |
|-----------|--------|
| Claude Code 미설치 | 안내 후 중단 |
| Node.js 미설치 | 안내 후 중단 |
| Cargo 미설치 | RTK + docs 빌드 도구(mdbook, mdbook-mermaid) 스킵, 경고 출력 후 계속 |
| MCP 서버 등록 실패 | 해당 서버만 실패 표시, 계속 진행 |
| 네트워크 오류 | 재시도 안내, 수동 명령어 제시 |
| 이미 설치된 항목 | 스킵, 현재 버전 표시 |
