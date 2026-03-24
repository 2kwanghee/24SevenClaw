# 24SevenClaw - Agent Communication Protocol

## 1. 개요

Agent와 Cloud 간의 통신은 **WebSocket(WSS)** 기반이며, Agent가 Cloud로 아웃바운드 연결을 맺는다.

```
Agent ──── WSS (outbound, port 443) ────► Cloud WebSocket Hub
```

---

## 2. 연결 라이프사이클

### 2.1 최초 등록

```
1. 관리자가 Cloud UI에서 "Agent 추가" → agent_id + registration_token 발급
2. 고객 서버에 Agent 설치: install.sh --token <registration_token>
3. Agent 시작 → Cloud에 WebSocket 연결
4. Agent → Cloud: agent.register 메시지 전송
5. Cloud: 토큰 검증 → agent_secret 발급 → DB에 Agent 등록
6. Agent: agent_secret을 로컬에 저장 (이후 인증에 사용)
```

### 2.2 일반 연결 (재시작 시)

```
1. Agent 시작 → 저장된 agent_secret으로 WebSocket 연결
2. 연결 URL: wss://api.24sevenclaw.com/ws/agent?agent_id={id}
3. HTTP 헤더: Authorization: Bearer {agent_secret}
4. Cloud: 인증 확인 → 연결 수립
5. Agent: 즉시 heartbeat 전송 (현재 상태 포함)
```

### 2.3 연결 유지

```
Agent ──(30초 간격)──► agent.heartbeat
Cloud ──(응답)──────► heartbeat.ack

60초간 heartbeat 없음 → Cloud가 Agent를 "offline"으로 표시
```

### 2.4 재연결 전략

```
연결 끊김 감지 → 즉시 재연결 시도
실패 시 → 지수 백오프: 1s → 2s → 4s → 8s → ... → max 300s (5분)
재연결 성공 → 백오프 리셋 + 밀린 상태 보고 전송
```

---

## 3. 메시지 포맷

모든 메시지는 JSON 형식이며 공통 envelope을 사용한다.

### 3.1 공통 Envelope

```json
{
  "id": "msg_uuid_v4",
  "type": "agent.heartbeat | command.setup_env | ...",
  "timestamp": "2026-03-23T10:30:00Z",
  "payload": { ... },
  "signature": "hmac_sha256_hex"   // agent_secret으로 서명
}
```

### 3.2 서명 검증

```
signature = HMAC-SHA256(
  key = agent_secret,
  message = id + type + timestamp + JSON(payload)
)
```

양방향 모두 서명 검증. 검증 실패 → 메시지 무시 + 경고 로그.

---

## 4. 메시지 타입 정의

### 4.1 Agent → Cloud

#### `agent.register`
최초 등록 요청.
```json
{
  "type": "agent.register",
  "payload": {
    "registration_token": "reg_xxxxx",
    "hostname": "customer-server-01",
    "os": "Ubuntu 24.04",
    "docker_version": "27.0.3",
    "agent_version": "1.0.0",
    "capabilities": ["docker", "git", "claude", "build"]
  }
}
```

#### `agent.heartbeat`
주기적 상태 보고 (30초).
```json
{
  "type": "agent.heartbeat",
  "payload": {
    "status": "idle | busy | error",
    "uptime_seconds": 86400,
    "system": {
      "cpu_percent": 23.5,
      "memory_percent": 45.2,
      "disk_percent": 60.1
    },
    "environments": [
      {
        "project_id": "proj_xxx",
        "status": "running | stopped | error",
        "containers": 4,
        "uptime_seconds": 3600
      }
    ],
    "active_tasks": ["task_xxx"]
  }
}
```

#### `agent.status`
환경/작업 상태 변경 이벤트 (즉시 전송).
```json
{
  "type": "agent.status",
  "payload": {
    "event": "env.created | env.started | env.stopped | env.error | task.started | task.completed | task.failed",
    "project_id": "proj_xxx",
    "task_id": "task_xxx",
    "detail": {
      "message": "Docker 환경 생성 완료",
      "containers_created": ["agent-runtime", "skill-server", "mcp-server", "claude"],
      "duration_ms": 45000
    }
  }
}
```

#### `agent.log`
로그 스트리밍 (요약만, 원본은 고객 서버 로컬).
```json
{
  "type": "agent.log",
  "payload": {
    "project_id": "proj_xxx",
    "task_id": "task_xxx",
    "level": "info | warn | error",
    "source": "docker | claude | git | build",
    "message": "빌드 완료: 42개 파일 컴파일, 0 에러",
    "truncated": true
  }
}
```

#### `agent.result`
작업 완료 결과.
```json
{
  "type": "agent.result",
  "payload": {
    "task_id": "task_xxx",
    "ticket_id": "ticket_xxx",
    "status": "completed | failed | partial",
    "summary": "로그인 기능 구현 완료",
    "changes": {
      "files_created": ["src/auth/login.py", "tests/test_login.py"],
      "files_modified": ["src/main.py"],
      "files_deleted": [],
      "git_commit": "abc1234",
      "git_branch": "feature/login"
    },
    "metrics": {
      "duration_ms": 120000,
      "tokens_used": 15000
    }
  }
}
```

---

### 4.2 Cloud → Agent

#### `command.setup_env`
환경 프로비저닝 명령.
```json
{
  "type": "command.setup_env",
  "payload": {
    "project_id": "proj_xxx",
    "project_name": "my-ai-project",
    "environment": {
      "template": "python-agent",
      "agents": [
        {
          "id": "agent_xxx",
          "name": "code-writer",
          "image": "registry.24sevenclaw.com/agents/code-writer:1.2.0",
          "config": { "model": "claude-sonnet-4-6", "max_tokens": 8000 }
        }
      ],
      "skills": [
        {
          "id": "skill_xxx",
          "name": "web-search",
          "image": "registry.24sevenclaw.com/skills/web-search:1.0.0",
          "config": { "api_key_env": "SEARCH_API_KEY" }
        }
      ],
      "mcps": [
        {
          "id": "mcp_xxx",
          "name": "github-mcp",
          "image": "registry.24sevenclaw.com/mcps/github:2.0.0",
          "config": { "transport": "streamable_http", "port": 3100 }
        }
      ],
      "claude": {
        "version": "latest",
        "api_key_env": "ANTHROPIC_API_KEY"
      }
    },
    "git": {
      "init": true,
      "remote_url": "git@github.com:customer/my-project.git",
      "branch": "main"
    }
  }
}
```

#### `command.deploy_ticket`
개발 티켓 전달.
```json
{
  "type": "command.deploy_ticket",
  "payload": {
    "ticket_id": "ticket_xxx",
    "project_id": "proj_xxx",
    "title": "사용자 로그인 기능 구현",
    "description": "이메일/비밀번호 기반 로그인 API와 JWT 토큰 발급 구현",
    "priority": "high",
    "acceptance_criteria": [
      "POST /api/auth/login 엔드포인트 구현",
      "JWT access/refresh 토큰 발급",
      "비밀번호 bcrypt 해싱",
      "단위 테스트 작성"
    ],
    "context": {
      "related_files": ["src/auth/", "src/models/user.py"],
      "branch": "feature/login"
    }
  }
}
```

#### `command.build`
빌드 실행 명령.
```json
{
  "type": "command.build",
  "payload": {
    "project_id": "proj_xxx",
    "build_type": "full | incremental",
    "command": "npm run build",
    "env_vars": { "NODE_ENV": "production" },
    "stream_logs": true
  }
}
```

#### `command.run`
서비스 실행 명령.
```json
{
  "type": "command.run",
  "payload": {
    "project_id": "proj_xxx",
    "command": "npm start",
    "port": 3000,
    "env_vars": { "PORT": "3000" }
  }
}
```

#### `command.stop`
서비스 중지.
```json
{
  "type": "command.stop",
  "payload": {
    "project_id": "proj_xxx",
    "target": "all | build | service",
    "force": false
  }
}
```

#### `command.destroy_env`
환경 삭제.
```json
{
  "type": "command.destroy_env",
  "payload": {
    "project_id": "proj_xxx",
    "keep_git": true,
    "keep_data": false
  }
}
```

#### `config.update`
설정 변경 (에이전트/스킬/MCP 추가/제거/수정).
```json
{
  "type": "config.update",
  "payload": {
    "project_id": "proj_xxx",
    "changes": [
      {
        "action": "add | remove | update",
        "target": "agent | skill | mcp",
        "id": "agent_xxx",
        "config": { ... }
      }
    ]
  }
}
```

---

## 5. 에러 처리

### 5.1 에러 응답 포맷
```json
{
  "type": "error",
  "payload": {
    "code": "ENV_SETUP_FAILED | DOCKER_ERROR | AUTH_FAILED | LICENSE_EXPIRED | ...",
    "message": "Docker 이미지 pull 실패: registry.24sevenclaw.com/agents/code-writer:1.2.0",
    "original_message_id": "msg_xxx",
    "recoverable": true,
    "suggestion": "네트워크 연결을 확인하거나 이미지 태그를 확인하세요"
  }
}
```

### 5.2 에러 코드

| 코드 | 설명 | 복구 가능 |
|------|------|-----------|
| `AUTH_FAILED` | 인증 실패 | No - 재등록 필요 |
| `LICENSE_EXPIRED` | 라이센스 만료 | No - 갱신 필요 |
| `LICENSE_LIMIT` | 라이센스 한도 초과 | No - 업그레이드 필요 |
| `DOCKER_ERROR` | Docker 작업 실패 | Yes - 재시도 |
| `ENV_SETUP_FAILED` | 환경 구성 실패 | Yes - 재시도 |
| `GIT_ERROR` | Git 작업 실패 | Yes - 재시도 |
| `CLAUDE_ERROR` | Claude 작업 실패 | Yes - 재시도 |
| `BUILD_FAILED` | 빌드 실패 | Yes - 수정 후 재시도 |
| `RESOURCE_LIMIT` | 서버 리소스 부족 | No - 리소스 확보 필요 |
| `TIMEOUT` | 작업 시간 초과 | Yes - 재시도 |

---

## 6. 보안

### 6.1 인증 흐름
```
[최초 등록]
Cloud UI → registration_token 발급
Agent → Cloud: registration_token으로 등록
Cloud → Agent: agent_id + agent_secret 발급

[이후 연결]
Agent → Cloud: WebSocket 연결 시 Authorization 헤더에 agent_secret
Cloud: agent_secret 검증 + 라이센스 유효성 확인
```

### 6.2 보안 원칙
- 모든 통신 TLS 암호화 (WSS)
- 메시지별 HMAC-SHA256 서명
- agent_secret은 고객 서버에만 저장 (클라우드는 해시만 보관)
- 민감 정보(API 키 등)는 절대 클라우드로 전송하지 않음
- 환경 변수 참조(`_env` 접미사)로 민감값 처리

### 6.3 라이센스 검증
```
Agent 시작 → Cloud에 라이센스 확인 요청
Cloud: 라이센스 유효 → 정상 동작
Cloud: 라이센스 만료 → Agent를 읽기 전용 모드로 전환
Cloud: 라이센스 없음 → Agent 연결 거부

주기적 검증: 24시간마다 + Cloud에서 push 가능
오프라인 허용: 마지막 검증 후 72시간까지 (grace period)
```
