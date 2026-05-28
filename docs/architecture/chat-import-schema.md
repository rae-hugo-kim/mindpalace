# Claude Chat Import Schema (사용자 가공 JSON)

**Source**: 사용자가 Claude.ai 공식 export(요청 후 메일 수신)를 받아 본인 채팅만 분리/가공한 JSON.
**Schema version**: 1 (in-file `schema_version` 필드)
**Confirmed**: 2026-05-26 (`data/imports/claude-chat/chat-export.json`, 91MB, 402 conversations, 6803 messages, 0 other_users_excluded)

이 명세는 v0 import 모듈의 **권위 있는 입력 컨트랙트**. Anthropic 공식 export 포맷에 직접 의존하지 않고, 사용자가 가공한 안정적 형식을 사용함 (CRITICAL #1 해소).

## Top-level (dict)

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | 1 |
| `exported_at` | ISO timestamp | export 가공 시점 |
| `source_export_root` | str | 원본 export 경로 (anonymized) |
| `user` | dict | `{email_address, full_name, uuid}` |
| `summary` | dict | 통계 요약 (`conversations`, `messages_total`, `projects_created_by_user`, `design_chats.*`) |
| `notes` | dict | 사용자가 작성한 처리 정책 메모 (`design_chats`, `scope_choice` 등) |
| `conversations` | list | 채팅 세션 N개 (메인 데이터, v0 import 대상) |
| `projects` | list | Claude Projects (참조 메타, v1+) |
| `design_chats` | dict | `{in_user_projects, orphans, unattributable}` 분류 |

## conversation (in `conversations[]`)

| Field | Type | Used by v0 import? | Notes |
|---|---|---|---|
| `uuid` | str | YES — dedup key (1차) | 세션 고유 ID |
| `name` | str | YES — **표제어** | 채팅 제목 (검색 메타) |
| `summary` | str | YES — lazy 메타 (선택) | 사용자가 미리 가공해 둔 요약. 시스템 ingest 가공 금지 원칙과 충돌하지 않음 (사용자 제공이므로) |
| `created_at` | ISO timestamp | YES — 시간 단서 | |
| `updated_at` | ISO timestamp | YES — 시간 단서 | |
| `account` | dict | NO | `{uuid}` only — user 검증용 |
| `chat_messages` | list | YES — 청크 원천 | 메시지들 |

## message (in `conversation.chat_messages[]`)

| Field | Type | Used by v0 import? | Notes |
|---|---|---|---|
| `uuid` | str | YES — dedup key (2차) | 메시지 고유 ID |
| `text` | str | YES — **청크 텍스트** | 평탄화된 본문 (v0 사용) |
| `content` | list[dict] | NO (v1+) | 구조화된 본문 — `citations`, `flags`, `start_timestamp`, `stop_timestamp`, `text`, `type`. 코드 블록·인용 처리 시 필요 |
| `sender` | str | YES — 메타 | `'human'` or `'assistant'` |
| `created_at` | ISO timestamp | YES | |
| `updated_at` | ISO timestamp | YES | |
| `parent_message_uuid` | str | NO (v1+) | 메시지 트리 — branching/edits 표현 |
| `attachments` | list | NO (v1+) | 첨부 파일 (대부분 빈 리스트) |
| `files` | list | NO (v1+) | 동상 |

## Import Contract (v0)

- **청크 단위**: 1 message = 1 chunk (turn 단위). Code 세션과 동일 청크 정책.
- **청크 텍스트**: `message.text` (구조화된 `content`는 v1+).
- **청크 메타**:
  - `conversation.uuid` (세션 식별)
  - `conversation.name` (표제어 — 검색/약한 연결 매칭)
  - `conversation.created_at` (시간 단서 — ±3일 학습-작업 연결)
  - `message.uuid` (메시지 식별)
  - `message.sender` (`human`/`assistant`)
  - `message.created_at`
  - `source` = `"claude-chat"` (다른 영역 = `"claude-code"`)
- **dedup**: `(conversation.uuid, message.uuid)` 조합을 고유키로 사용. 같은 conversation 재import 시 message 단위 dedup도 작동.
- **secret 마스킹**: 모든 청크 텍스트에 `mask_secrets()` 적용 — raw 보존본도 마스킹 후.
- **conversation.summary**: 별도 메타 컬럼으로 보존. 검색 시 매칭에 활용 (사용자 제공 요약).

## v0 범위 외 (v1+)

- `content[]` 구조화 처리 (citations, code blocks)
- `parent_message_uuid` 기반 메시지 트리/branching 표현
- `attachments`, `files` 처리
- `projects[]` 메타 통합 (각 conversation을 project에 연결)
- `design_chats.unattributable` 별도 표시

## 파일 위치 정책

- 입력: `data/imports/claude-chat/*.json` (gitignored)
- 같은 디렉토리에 신규 export 누적 시, 각 파일 단독 import 후 dedup으로 중복 흡수
