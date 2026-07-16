---
title: 통신 프로토콜
category: architecture
status: needs-revision
last_updated: 2026-07-16
related:
  - clickeye-api/app/ws
  - clickeye-agent
  - clickeye-contracts/protocol/commands.ts
  - clickeye-contracts/protocol/messages.ts
---

# ClickEye - Communication Protocol

## 1. 개요

현재 ClickEye의 통신은 **브라우저 ↔ Cloud API** 간 HTTPS 기반이며, ZIP 다운로드 방식으로 사용자에게 파일을 전달한다.

```
Browser ──── HTTPS ────► Cloud API ──── ZIP Stream ────► Browser
```

> **Phase 2 예정**: CLI ↔ Cloud 통신 (설정 동기화), WebSocket (대시보드 실시간 업데이트)

---

## 2. 인증

### 2.1 웹 인증 (현재 구현)

```
1. 사용자가 회원가입 (POST /api/v1/auth/register)
2. 로그인 (POST /api/v1/auth/login) → JWT 발급
3. 이후 API 호출 시 Authorization: Bearer {jwt} 헤더 포함
```

### 2.2 토큰 구조

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

Auth.js v5 (next-auth) + JWT 전략 사용. 서버 세션 없이 토큰 기반 인증.

---

## 3. API 엔드포인트

### 3.1 인증 (완료)

#### `POST /api/v1/auth/register`
```json
// Request
{ "email": "user@example.com", "password": "securepass", "name": "홍길동" }

// Response (201)
{ "id": "uuid", "email": "user@example.com", "name": "홍길동" }
```

#### `POST /api/v1/auth/login`
```json
// Request
{ "email": "user@example.com", "password": "securepass" }

// Response (200)
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

---

### 3.2 조직 (LoadMap_v3)

#### `POST /api/v1/organizations`
회사 정보 등록/수정.
```json
// Request
{
  "company_name": "스타트업 주식회사",
  "size": "small",
  "industry": "it",
  "tech_stack": ["python", "react", "postgresql"]
}

// Response (200)
{ "id": "uuid", "company_name": "스타트업 주식회사", ... }
```

#### `GET /api/v1/organizations/me`
내 회사 정보 조회.

---

### 3.3 카탈로그 (LoadMap_v3)

#### `GET /api/v1/catalog/agents`
에이전트 목록 (JSON 파일 기반).
```json
// Response (200)
[
  { "id": "backend", "name": "시니어 백엔드 엔지니어", "description": "...", "outputFile": "api-agent.md" },
  { "id": "frontend", "name": "프론트엔드 전문가", ... },
  ...
]
```

#### `GET /api/v1/catalog/skills`
스킬 목록 (워크플로우 + 외부 도구).
```json
// Response (200)
[
  { "id": "tdd", "name": "TDD 스마트 코딩", "requiresApiKey": false },
  { "id": "linear", "name": "Linear 연동", "requiresApiKey": true, "envVars": ["LINEAR_API_KEY"] },
  ...
]
```

#### `GET /api/v1/catalog/platforms`
Agent 플랫폼 목록.

#### `GET /api/v1/catalog/pipelines`
자동화 파이프라인 목록.

---

### 3.4 프로젝트 설정 (LoadMap_v3)

#### `POST /api/v1/projects/{id}/config`
위저드 전체 결과 저장.
```json
// Request
{
  "organization": { "company_name": "...", "size": "small", "industry": "it" },
  "solution": { "project_name": "my-saas", "type": "saas", "stack": "fastapi-nextjs", "description": "..." },
  "agents": ["backend", "frontend", "harness"],
  "skills": ["tdd", "linear", "telegram"],
  "pipelines": ["harness", "tdd", "lint-gate"],
  "platform": "claude-code"
}
```

#### `GET /api/v1/projects/{id}/config`
위저드 설정 조회 (재다운로드용).

---

### 3.5 프리뷰 + ZIP 생성 (LoadMap_v3)

#### `POST /api/v1/projects/{id}/preview`
파일 트리 + 내용 프리뷰.
```json
// Request
{ /* 위저드 설정과 동일 */ }

// Response (200)
{
  "fileTree": [
    { "path": "CLAUDE.md", "type": "file" },
    { "path": ".claude/", "type": "directory" },
    { "path": ".claude/agents/api-agent.md", "type": "file" },
    ...
  ],
  "files": {
    "CLAUDE.md": "# My SaaS Project\n...",
    ".claude/agents/api-agent.md": "# 시니어 백엔드 엔지니어\n...",
    ...
  }
}
```

#### `POST /api/v1/projects/{id}/generate`
ZIP 파일 스트리밍 다운로드.
```json
// Request
{
  /* 위저드 설정 */
  "envVars": {
    "LINEAR_API_KEY": "lin_xxx",
    "TELEGRAM_BOT_TOKEN": "123:ABC"
  }
}

// Response
// Content-Type: application/zip
// Content-Disposition: attachment; filename="my-saas.zip"
// (ZIP 바이너리 스트림)
```

> **보안**: envVars는 메모리에서만 처리. DB/로그에 기록하지 않음.

---

### 3.6 추천 (LoadMap_v3)

#### `POST /api/v1/recommend`
솔루션 유형 기반 추천.
```json
// Request
{ "solution_type": "saas", "industry": "it" }

// Response (200)
{
  "agents": ["backend", "frontend", "devops"],
  "skills": ["tdd", "linear", "harness-gate"],
  "pipelines": ["harness", "tdd", "lint-gate"]
}
```

---

## 4. 에러 처리

### 4.1 HTTP 에러 응답

```json
{
  "detail": "이메일이 이미 등록되어 있습니다."
}
```

### 4.2 에러 코드

| HTTP | 설명 | 대응 |
|------|------|------|
| 400 | 요청 유효성 검사 실패 | 입력값 확인 |
| 401 | 인증 실패/토큰 만료 | 재로그인 |
| 403 | 권한 없음 / 라이센스 초과 (Phase 2) | 플랜 확인 |
| 404 | 리소스 없음 | ID 확인 |
| 422 | Pydantic 밸리데이션 실패 | 필드 확인 |
| 500 | 서버 오류 | 재시도 |

---

## 5. 보안

### 5.1 인증 흐름
```
[회원가입/로그인]
Browser → Cloud API: email + password
Cloud → Browser: JWT (access_token)

[이후 API 호출]
Browser → Cloud API: Authorization: Bearer {jwt}
Cloud: JWT 검증
```

### 5.2 보안 원칙
- 모든 통신 TLS 암호화 (HTTPS)
- JWT 기반 stateless 인증
- 사용자 외부 도구 API 키는 서버에 **저장하지 않음** (.env → ZIP에만 포함)
- 사용자의 AI API 키 (Claude, Gemini)는 절대 서버로 전송하지 않음
- 비밀번호는 bcrypt 해싱

---

## 6. Phase 2 확장 예정

### 6.1 CLI ↔ Cloud 통신
```
CLI ──── HTTPS ────► Cloud API
  - POST /api/cli/auth           # CLI 토큰 인증
  - GET  /projects/{id}/config   # 설정 동기화
  - POST /projects/{id}/events   # 진행 상태 보고
```

### 6.2 WebSocket (대시보드 실시간)
```
Browser ──── WSS ────► Cloud WebSocket
  - project.event     # CLI가 보고한 이벤트 실시간 전달
  - project.status    # 프로젝트 상태 변경 알림
```

### 6.3 라이센스 검증
```
CLI 실행 시 → JWT 클레임에서 라이센스 상태 확인
유효 → 정상 동작
만료 → 기능 제한 + 웹에서 갱신 안내
```

---

## 7. Runner 태스크 프로토콜 (위치 무관 실행 계약)

> SI 팩토리 전환 P0 — CE-301. 설계 근거: `docs/si-factory-transition.md` §1.1(실행 계층 균일 추상화), §2.4·§3.2(하이브리드 러너 패턴).
> 계약 SSOT: `clickeye-contracts/protocol/commands.ts`(`RunnerTaskPayload`), `messages.ts`(`command.run_task`, `StatusPayload`/`LogPayload`/`ResultPayload`) + Python 미러 `python/protocol.py`.

### 7.1 목적 — 위치 무관 실행

**데스크탑 러너**(구독 시트, 주력)와 **클라우드 컨테이너**(조직 API 키, 폴백)가 **동일하게 소비**하는 하나의 실행 계약이다. 컨트롤 플레인은 실행 위치에 무관하게 동일한 `RunnerTaskPayload`를 발신하고, 러너는 자신의 팔(`target`)에 맞게 이를 해석한다.

- **데스크탑 러너** = `target: "desktop"` → `claude -p` claude.ai 구독 세션 (주력, §2.1)
- **클라우드 컨테이너** = `target: "cloud"` → `clickeye-agent`가 컨테이너 내에서 조직 API 키로 실행 (폴백)

### 7.2 흐름 — 요청 → 상태 → 로그 → 결과

```
컨트롤 플레인 ──[command.run_task: RunnerTaskPayload(task_id 발급)]──► 러너(desktop|cloud)
러너 ──[agent.status: StatusPayload(task_id)]──────────► 진행 상태 (진행률/이벤트)
러너 ──[agent.log:    LogPayload(task_id)]─────────────► 로그 스트리밍 (streaming.logs)
러너 ──[agent.result: ResultPayload(task_id)]──────────► 최종 결과 (완료/실패/부분 + 변경/메트릭)
```

**task_id 상관관계**: 발신 주체(컨트롤 플레인)가 `task_id`를 발급하고, 이후 모든 상태·로그·결과 메시지가 동일 `task_id`를 실어 하나의 태스크로 묶인다. `HeartbeatPayload.active_tasks`는 러너가 현재 실행 중인 `task_id` 목록을 보고한다.

### 7.3 `RunnerTaskPayload` (`command.run_task`)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `task_id` | string | ✅ | 상관관계 키. 컨트롤 플레인이 발급, status/log/result가 공유 |
| `project_id` | string | ✅ | 프로젝트 식별자 |
| `target` | `"cloud" \| "desktop"` | ✅ | 실행 팔. desktop=구독 시트 주력 / cloud=조직 키 폴백 |
| `auth_mode` | `"subscription_seat" \| "org_api_key"` | | 하이브리드 인증 결정. 미지정 시 `target` 기본값 |
| `ticket_id` | string | △ | 작업 단위 = Linear 이슈(§1.1). 러너가 이슈를 컨텍스트로 실행 |
| `prompt` | string | △ | AI 코딩 지시 (desktop=`claude -p` 세션 / cloud=컨테이너 내 동일 세션) |
| `command` | string | △ | 순수 셸 명령 (AI 없이 빌드/스크립트 실행) |
| `model` | string | | 모델 라우팅 힌트(opus/sonnet/haiku). 미지정 시 러너 정책 기본값 |
| `streaming` | `{ logs?, artifacts? }` | | 로그·산출물 스트리밍 정책. 미지정 시 러너 기본값 |
| `timeout_seconds` | number | | 실행 타임아웃(**정수 초**). 초과 시 러너가 중단 후 result status=failed |

> **실행 명세 제약(△)**: `ticket_id` / `prompt` / `command` 중 **최소 하나 필수**. 조합 근거 — ticket_id(+prompt)=이슈 기반 AI 작업, prompt 단독=ad-hoc AI 작업, command 단독=비-AI 실행. TypeScript 인터페이스로 "최소 하나" 제약은 표현 불가하므로 소비 핸들러가 런타임 검증한다(P1/P3 범위). 이 '최소 하나' 제약은 Python 미러 `RunnerTaskPayload`의 `model_validator(mode="after")`로 강제된다(W1).

### 7.4 결과 회계 (`ResultPayload` 확장)

`ResultPayload`에 optional `target` / `auth_mode`를 추가해, LLM 게이트웨이+원장(CE-299)이 **구독 시트 vs 조직 키** 비용을 실행 팔별로 구분 집계할 수 있게 한다.

> **범위 밖 TODO**: (1) `clickeye-agent`의 `DockerHandler` 실행 핸들러 스키마를 본 계약에 정합화(P1/P3). (2) `contract_service.py`의 `'contract.sync'` 문자열 ↔ 계약면 `'command.contract_sync'` 불일치 통일(별도 티켓). 이번 범위는 계약 스키마 확정만.
