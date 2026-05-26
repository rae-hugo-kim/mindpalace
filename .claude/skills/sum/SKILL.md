---
name: sum
allowed-tools: Write, Bash(mkdir:*)
argument-hint: [filename]
description: Summarizes the current conversation to docs/sum/. Use when the user says "sum", "요약해줘", "정리해줘", "요약문서 만들어줘", "세션 저장", or wants to preserve session context.
---

# Sum - Summarize Conversation

## Goal

Summarize the current conversation to a markdown file for future reference.
**단순 요약이 아니라, 이후 세션에서 같은 문제를 반복하지 않도록 "어떻게 해결했는지"까지 기록한다.**

## Inputs

- `$ARGUMENTS`: Custom filename (optional). Default: `session_YYYY-MM-DD_<topic>.md`

## Output Path

```
<project-root>/docs/sum/<filename>.md
```

If `docs/sum/` doesn't exist, create it.

## Process

### 1. Create output directory

```bash
mkdir -p docs/sum
```

### 2. Generate summary

Analyze the conversation and extract the following. **특히 Fixes & Troubleshooting, Implementation Details 섹션은 반드시 충실하게 작성한다.**

```markdown
# Session Summary: <main topic>

**Date**: YYYY-MM-DD
**Duration**: ~N messages

## Overview
1-3문장으로 이 세션에서 무슨 작업을 했는지 요약.

## Key Decisions
- Decision 1: <what was decided> — **Why**: <근거/맥락>
- Decision 2: <what was decided> — **Why**: <근거/맥락>

## Work Completed
- [x] Task 1 — <status/outcome>
- [x] Task 2 — <status/outcome>

## Fixes & Troubleshooting

이 세션에서 해결한 오류/버그/문제를 각각 아래 형식으로 기록한다.
오류가 없었으면 이 섹션을 "이 세션에서 해결한 오류 없음"으로 표기.

### Fix 1: <문제 한 줄 요약>

**증상**: 어떤 현상이 발생했는지 (에러 메시지, 잘못된 동작 등)

**원인**: 왜 발생했는지 (근본 원인)

**해결**:
- 어떤 파일의 어떤 부분을 어떻게 수정했는지
- 변경 전/후 코드 또는 설정 (핵심 diff만)

```diff
- 변경 전 코드
+ 변경 후 코드
```

**교훈**: 다음에 비슷한 상황에서 기억할 점

---

(Fix 2, Fix 3... 동일 형식으로 반복)

## Implementation Details

이 세션에서 새로 구현하거나 크게 변경한 기능을 각각 아래 형식으로 기록한다.
단순 수정(오타, 1줄 변경 등)은 생략 가능.

### Feature/Change 1: <기능 한 줄 요약>

**목적**: 왜 이 기능이 필요했는지

**구현 방식**:
- 어떤 접근을 택했는지, 왜 그 접근인지
- 핵심 로직 설명 (코드 발췌 포함)
- 관련 파일: `path/to/file`

**주의사항**: 이 구현에서 알아둘 점, 제약, edge case

---

(Feature/Change 2... 동일 형식으로 반복)

## Files Changed
- `path/to/file1` — <what changed>
- `path/to/file2` — <what changed>

## Open Items
- Item needing follow-up
- Unresolved question

## Notes
<추가 맥락, 향후 참고사항>
```

### 3. Writing Guidelines

| 원칙 | 설명 |
|------|------|
| **재현 가능하게** | 같은 문제가 생기면 이 문서만 보고 해결할 수 있어야 함 |
| **핵심 diff 포함** | 변경 전/후를 diff 블록으로 보여줌. 전체 코드 복붙 X, 핵심만 |
| **원인-해결 연결** | "뭘 바꿨다"만이 아니라 "왜 그게 문제였고 왜 이렇게 바꿨다"를 씀 |
| **교훈 명시** | 반복 방지를 위해 "다음에 기억할 점"을 Fix마다 남김 |
| **불필요한 장황함 X** | 자세하되 군더더기 없이. 관련 없는 시행착오는 생략 |

### 4. Save file

Write to `docs/sum/<filename>.md`

### 5. Output

Report: `File saved: docs/sum/<filename>.md`

### 6. Clear context (optional)

After saving, suggest `/clear` to reset conversation context.

## Error Handling

| Condition | Action |
|-----------|--------|
| Can't create directory | Report error, suggest manual creation |
| No meaningful content | Create minimal summary, note "short session" |
| No fixes in session | Fixes & Troubleshooting 섹션에 "해결한 오류 없음" 표기 |
| No new features | Implementation Details 섹션에 "새로운 구현 없음" 표기 |
