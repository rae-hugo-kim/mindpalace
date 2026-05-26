---
name: init
allowed-tools: Read, Bash(gh:*), Bash(cd:*), Bash(git:*), Bash(rm:*), Bash(echo:*), Bash(date:*), Bash(ls:*), Bash(mkdir:*), Write, Edit, AskUserQuestion
argument-hint: <project-name> [--private]
description: Create a new project from the claude template repository
---

# Init - New Project from Template

## Goal

템플릿 리포지토리(rae-hugo-kim/claude)에서 새 프로젝트를 생성하고, 바로 작업 가능한 상태로 만든다.

## Inputs

- `$ARGUMENTS`: 프로젝트 이름 (필수)
  - `"my-app"` → public repo 생성
  - `"my-app --private"` → private repo 생성
  - 이름 없이 실행 → AskUserQuestion으로 물어봄

## Non-Negotiables

| Rule | Violation = STOP |
|------|------------------|
| **프로젝트 이름 필수** | 이름 없으면 물어봐야 함 |
| **gh CLI 인증 확인** | 미인증이면 안내 후 중단 |
| **플레이스홀더 정리** | 이전 프로젝트 흔적 남기지 않음 |

## Workflow

### Phase 0: Pre-flight

```
1. gh auth status 확인 → 실패 시 "! gh auth login을 실행하세요" 안내 후 중단
2. $ARGUMENTS에서 프로젝트 이름 추출
3. 이름 없으면 AskUserQuestion으로 물어봄
4. --private 플래그 확인
```

### Phase 1: Repository 생성

```bash
gh repo create <project-name> --template rae-hugo-kim/claude [--private] --clone
cd <project-name>
```

생성 실패 시:
- 이미 존재하는 repo → 알림 후 중단
- 네트워크 오류 → 재시도 안내

### Phase 2: 플레이스홀더 정리

하네스 파일들을 깨끗한 상태로 초기화:

```
1. docs/harness/ 정리:
   - seed.yaml → 삭제 (kickoff에서 새로 생성)
   - rubric-report.md → 삭제
   - audit.jsonl → 비움 (빈 파일로)
   - kickoff-summary.md → 삭제
   - kickoff-done → 삭제 (있으면)
   - current-scope.md → 삭제 (있으면)
   - README.md → 유지

2. docs/glossary.yaml → 템플릿에서 복사하여 terms: [] 로 초기화

3. docs/sum/ → 비움 (이전 세션 기록 제거)

4. README 교체 (템플릿 README가 derived repo에 새지 않도록):
   - README.md, README.en.md를 아래 placeholder로 덮어쓴다.
   - `<!-- claude-template-placeholder -->` 마커는 `/kickoff`이 "아직 사용자가 손대지 않음"을 판별하는 데 사용된다.
```

**README.md placeholder**:

```markdown
**[English](README.en.md)**

# <project-name>

> TODO — 프로젝트 설명. `/kickoff` 실행 시 kickoff 결과로 자동 채워집니다.

<!-- claude-template-placeholder -->
```

**README.en.md placeholder**:

```markdown
**[한국어](README.md)**

# <project-name>

> TODO — Project description. Will be auto-filled when you run `/kickoff`.

<!-- claude-template-placeholder -->
```

`<project-name>`은 Phase 0에서 추출한 이름으로 치환한다.

### Phase 3: 하네스 메타 주입

`source_remote`, `commit_sha`, `bootstrapped_at`을 `.claude/hooks/harness/harness-meta.json`에 주입.
이 필드들이 있으면 SessionStart 훅이 원격 버전을 확인할 수 있고, 없으면(=템플릿 자체일 때) 스킵됨.

```bash
# 소스 레포 URL (SSH 형식 권장 — 비공개 접근 호환)
SOURCE_REMOTE="git@github.com:rae-hugo-kim/claude.git"

# 템플릿 현재 HEAD SHA — 사용자가 클론한 시점의 SHA
COMMIT_SHA=$(git -C . rev-parse HEAD)

# ISO 8601 UTC
BOOTSTRAPPED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

기존 `harness-meta.json`에 다음 필드 추가 (기존 `version`, `updated`, `description`은 유지):

```json
{
  "version": "<existing>",
  "updated": "<existing>",
  "description": "<existing>",
  "source_remote": "git@github.com:rae-hugo-kim/claude.git",
  "commit_sha": "<COMMIT_SHA>",
  "bootstrapped_at": "<BOOTSTRAPPED_AT>"
}
```

Edit 툴로 JSON 파일 직접 수정 (마지막 `}` 앞에 세 필드 삽입).

### Phase 4: 초기 커밋

```bash
git add -A
git commit -m "chore: initialize from claude template"
git push
```

### Phase 4: 안내

```markdown
## Project Ready: <project-name>

- Repository: https://github.com/<owner>/<project-name>
- Local path: <path>

### Next Steps
1. `cd <project-name>`
2. `/kickoff` — 프로젝트 스코프 정의
3. `/startdev` — TDD 기반 구현 시작

### Included
- 8 skills: bootstrap, init, kickoff, startdev, sum, compr, compush, tidy
- 7 hooks: scope-gate, context-gate, acceptance-gate, backpressure-gate, kickoff-detector, read-tracker, backpressure-tracker
- Rules, templates, glossary
```

## Error Handling

| Condition | Action |
|-----------|--------|
| gh 미설치 | "gh CLI를 설치하세요: https://cli.github.com" |
| gh 미인증 | "! gh auth login을 실행하세요" |
| repo 이름 충돌 | "이미 존재합니다. 다른 이름을 사용하세요" |
| template 접근 불가 | "rae-hugo-kim/claude 접근 권한을 확인하세요" |
| clone 실패 | 네트워크 확인 안내 |
