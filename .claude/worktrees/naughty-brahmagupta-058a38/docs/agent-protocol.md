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
