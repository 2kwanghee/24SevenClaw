# 24SevenClaw - CLI ↔ Cloud Communication Protocol

## 1. 개요

CLI와 Cloud 간의 통신은 **HTTPS** 기반이며, CLI가 Cloud API에 요청을 보내는 단방향 구조다.

```
CLI ──── HTTPS (outbound) ────► Cloud API
```

브라우저 대시보드의 실시간 업데이트는 별도의 **WebSocket** 연결을 사용한다.

```
Browser ──── WSS ────► Cloud WebSocket (대시보드 실시간 업데이트)
```

---

## 2. 인증 라이프사이클

### 2.1 CLI 토큰 발급

```
1. 사용자가 Cloud 웹 UI에서 프로젝트 생성 완료
2. "CLI 설치" 페이지에서 CLI 토큰 발급 (cli_token)
3. 사용자가 로컬에서: npx @24sevenclaw/cli init
4. CLI가 토큰 입력 요청 → 사용자가 cli_token 입력
5. CLI → Cloud: POST /api/cli/auth {cli_token}
6. Cloud: 토큰 검증 → access_token + refresh_token 발급
7. CLI: 로컬에 토큰 저장 (~/.24sc/credentials.json)
```

### 2.2 일반 인증 (재실행 시)

```
1. CLI 실행 → 저장된 access_token으로 API 요청
2. 만료 시 → refresh_token으로 자동 갱신
3. refresh_token도 만료 → 사용자에게 재인증 요청
```

### 2.3 토큰 구조

```json
{
  "access_token": "eyJhbGciOi...",   // JWT, 1시간 유효
  "refresh_token": "rt_xxxxx",       // 30일 유효
  "project_id": "proj_xxx",
  "expires_at": "2026-04-02T11:00:00Z"
}
```

---

## 3. API 엔드포인트

### 3.1 인증

#### `POST /api/cli/auth`
CLI 토큰으로 인증.
```json
// Request
{
  "cli_token": "ct_xxxxx"
}

// Response (200)
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "rt_xxxxx",
  "project_id": "proj_xxx",
  "project_name": "my-project",
  "expires_at": "2026-04-02T11:00:00Z"
}
```

#### `POST /api/cli/refresh`
토큰 갱신.
```json
// Request
{
  "refresh_token": "rt_xxxxx"
}

// Response (200)
{
  "access_token": "eyJhbGciOi...",
  "expires_at": "2026-04-02T12:00:00Z"
}
```

---

### 3.2 프로젝트 설정 다운로드

#### `GET /api/projects/{id}/config/download`
프로젝트 설정 전체 다운로드 (CLI init/setup에서 사용).
```json
// Response (200)
{
  "project": {
    "id": "proj_xxx",
    "name": "my-ai-project",
    "type": "webapp",
    "requirements": { ... },
    "deployment_type": "source_only",
    "target_os": "linux"
  },
  "template": {
    "name": "webapp",
    "scaffold": {
      "directories": ["src/", "tests/", "docs/"],
      "files": {
        "package.json": "{ ... }",
        "tsconfig.json": "{ ... }"
      }
    }
  },
  "agents": [
    {
      "id": "agent_xxx",
      "name": "code-writer",
      "type": "development",
      "config": {
        "model": "claude-sonnet-4-6",
        "instructions": "..."
      }
    }
  ],
  "skills": [
    {
      "id": "skill_xxx",
      "name": "web-search",
      "type": "tool",
      "config": { ... }
    }
  ],
  "hooks": [
    {
      "id": "hook_xxx",
      "event": "post-commit",
      "action": "report-status"
    }
  ],
  "claude_md_template": "# Project: {{project.name}}\n...",
  "config_version": 3
}
```

#### `GET /api/projects/{id}/config/version`
설정 버전 확인 (변경 감지용).
```json
// Response (200)
{
  "config_version": 3,
  "last_updated": "2026-04-02T10:30:00Z"
}
```

---

### 3.3 이벤트 보고

#### `POST /api/projects/{id}/events`
CLI가 진행 상태를 클라우드에 보고.
```json
// Request
{
  "event_type": "setup.completed | dev.started | milestone.progress | error",
  "data": {
    "message": "로컬 개발환경 구축 완료",
    "milestone_id": "ms_xxx",
    "progress_percent": 45,
    "files_changed": 12,
    "git_commit": "abc1234"
  }
}

// Response (200)
{
  "event_id": "evt_xxx",
  "received_at": "2026-04-02T10:30:00Z"
}
```

### 이벤트 타입

| 타입 | 설명 | 트리거 |
|------|------|--------|
| `setup.started` | CLI 환경 구축 시작 | `24sc setup` 실행 |
| `setup.completed` | CLI 환경 구축 완료 | `24sc setup` 완료 |
| `setup.failed` | CLI 환경 구축 실패 | `24sc setup` 실패 |
| `dev.started` | 개발 모드 시작 | `24sc dev` 실행 |
| `dev.stopped` | 개발 모드 종료 | `24sc dev` 종료 |
| `milestone.progress` | 마일스톤 진행 업데이트 | Claude Code 작업 완료 시 |
| `file.changed` | 파일 변경 보고 | Git 커밋 감지 시 |
| `error` | 에러 발생 | 모든 에러 |

---

### 3.4 설정 동기화

#### `GET /api/projects/{id}/config/diff?since_version={n}`
특정 버전 이후 변경사항만 다운로드 (sync에서 사용).
```json
// Response (200)
{
  "current_version": 5,
  "changes": [
    {
      "action": "add",
      "target": "skill",
      "item": { "id": "skill_yyy", "name": "database-query", ... }
    },
    {
      "action": "update",
      "target": "agent",
      "item": { "id": "agent_xxx", "config": { ... } }
    }
  ]
}
```

---

## 4. CLI 명령어 → API 매핑

| CLI 명령어 | API 호출 | 설명 |
|-----------|----------|------|
| `24sc init` | `POST /api/cli/auth` | 토큰 인증 |
| `24sc setup` | `GET /config/download` → `POST /events` | 설정 다운로드 + 스캐폴딩 + 완료 보고 |
| `24sc dev` | `POST /events (dev.started)` | 개발 모드 시작 보고 |
| `24sc status` | `POST /events (milestone.progress)` | 진행 상태 보고 |
| `24sc sync` | `GET /config/version` → `GET /config/diff` | 설정 변경 감지 + 동기화 |

---

## 5. 에러 처리

### 5.1 HTTP 에러 응답

```json
{
  "error": {
    "code": "AUTH_FAILED | LICENSE_EXPIRED | PROJECT_NOT_FOUND | ...",
    "message": "CLI 토큰이 만료되었습니다. 웹에서 새 토큰을 발급받으세요.",
    "recoverable": true,
    "suggestion": "24sc init 명령어로 재인증하세요"
  }
}
```

### 5.2 에러 코드

| 코드 | HTTP | 설명 | CLI 대응 |
|------|------|------|----------|
| `AUTH_FAILED` | 401 | 인증 실패/토큰 만료 | 재인증 안내 |
| `LICENSE_EXPIRED` | 403 | 라이센스 만료 | 웹에서 갱신 안내 |
| `LICENSE_LIMIT` | 403 | 프로젝트 한도 초과 | 업그레이드 안내 |
| `PROJECT_NOT_FOUND` | 404 | 프로젝트 없음 | 프로젝트 ID 확인 안내 |
| `CONFIG_VERSION_CONFLICT` | 409 | 설정 버전 충돌 | 전체 재다운로드 |
| `RATE_LIMITED` | 429 | 요청 횟수 초과 | 재시도 (Retry-After 헤더) |
| `SERVER_ERROR` | 500 | 서버 오류 | 재시도 |

---

## 6. 보안

### 6.1 인증 흐름
```
[CLI 토큰 발급]
Cloud 웹 UI → cli_token 발급 (1회용, 10분 유효)
CLI → Cloud: cli_token으로 인증
Cloud → CLI: access_token (1시간) + refresh_token (30일)

[이후 API 호출]
CLI → Cloud: Authorization: Bearer {access_token}
Cloud: JWT 검증 + 라이센스 유효성 확인
```

### 6.2 보안 원칙
- 모든 통신 TLS 암호화 (HTTPS)
- CLI 토큰은 1회용, 10분 유효 (재사용 불가)
- access_token은 로컬 파일에 저장 (권한 600)
- 사용자의 Anthropic API 키는 절대 클라우드로 전송하지 않음
- 이벤트 보고 시 코드 내용 미포함 (파일명, 변경 수만 전송)

### 6.3 라이센스 검증
```
CLI 실행 시 → access_token의 JWT 클레임에서 라이센스 상태 확인
라이센스 유효 → 정상 동작
라이센스 만료 → CLI 기능 제한 + 웹에서 갱신 안내
라이센스 없음 → CLI 인증 거부
```

---

## 7. 브라우저 WebSocket (대시보드 실시간)

CLI가 보고한 이벤트를 대시보드에 실시간으로 표시하기 위한 별도 WebSocket.

### 7.1 연결
```
Browser → WSS: wss://api.24sevenclaw.com/ws/project/{id}/stream
Authorization: Bearer {user_jwt}
```

### 7.2 서버 → 브라우저 메시지

```json
{
  "type": "project.event",
  "data": {
    "event_id": "evt_xxx",
    "event_type": "milestone.progress",
    "message": "로그인 기능 구현 완료 (45%)",
    "timestamp": "2026-04-02T10:30:00Z"
  }
}
```

### 7.3 흐름

```
CLI ─(HTTPS POST)─► Cloud API ─(Redis Pub/Sub)─► WebSocket ─► Browser
```

CLI가 이벤트를 보고하면, Cloud API가 Redis에 발행하고, WebSocket 서버가 구독하여 브라우저에 전달한다.
