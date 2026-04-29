# Contracts Agent — ClickEye Shared Protocol Development Guide

> 이 파일은 clickeye-contracts 모듈 개발 시 Claude Code가 참조하는 전담 가이드입니다.
> 레포 초기화 시 `clickeye-contracts/CLAUDE.md`로 복사합니다.

## 역할
- Cloud API의 OpenAPI 스펙 관리
- Agent↔Cloud WebSocket 메시지 프로토콜 정의
- TypeScript 타입/클라이언트 자동 생성
- 양쪽(web, api, agent)에서 공유하는 타입의 단일 진실 공급원(SSOT)

## Directory Structure
```
openapi/
├── openapi.json                # FastAPI에서 내보낸 REST API 스펙
└── openapi.yaml                # 사람이 읽기 쉬운 버전 (선택)

protocol/
├── messages.ts                 # WebSocket 메시지 타입 정의
├── commands.ts                 # Cloud → Agent 명령 타입
├── events.ts                   # Agent → Cloud 이벤트 타입
├── errors.ts                   # 에러 코드 및 타입
└── index.ts                    # 프로토콜 통합 export

generated/
└── typescript/
    ├── index.ts                # 자동 생성된 REST API 클라이언트
    ├── types.gen.ts            # 자동 생성된 타입
    └── services.gen.ts         # 자동 생성된 서비스 함수

python/
├── protocol.py                 # Python용 프로토콜 타입 (Pydantic)
└── __init__.py

scripts/
├── fetch-spec.sh               # API 서버에서 openapi.json 가져오기
├── generate-ts.sh              # TypeScript 클라이언트 생성
└── validate.sh                 # 스펙 유효성 검증

package.json
tsconfig.json
```

## Workflow

### OpenAPI 스펙 업데이트 흐름
```
1. [api] FastAPI에서 엔드포인트 추가/수정
2. [api] openapi_export.py 실행 → openapi.json 내보내기
3. [contracts] scripts/fetch-spec.sh → openapi.json 복사
4. [contracts] scripts/generate-ts.sh → TypeScript 타입/클라이언트 생성
5. [web] 생성된 타입으로 프론트엔드 코드 작성
```

### WebSocket 프로토콜 업데이트 흐름
```
1. [contracts] protocol/ 디렉토리에서 메시지 타입 정의
2. [contracts] python/ 디렉토리에서 Pydantic 모델 동기화
3. [api] Python 프로토콜 타입 사용하여 WebSocket Hub 구현
4. [agent] Python 프로토콜 타입 사용하여 Agent 메시지 처리
5. [web] TypeScript 프로토콜 타입 사용하여 UI 상태 표시
```

## Protocol Type Definitions

### TypeScript (protocol/messages.ts)
```typescript
// 공통 메시지 envelope
export interface Message<T = unknown> {
  id: string;
  type: MessageType;
  timestamp: string;
  payload: T;
  signature: string;
}

// Agent → Cloud
export type AgentMessageType =
  | 'agent.register'
  | 'agent.heartbeat'
  | 'agent.status'
  | 'agent.log'
  | 'agent.result';

// Cloud → Agent
export type CommandMessageType =
  | 'command.setup_env'
  | 'command.deploy_ticket'
  | 'command.build'
  | 'command.run'
  | 'command.stop'
  | 'command.destroy_env'
  | 'config.update';

export type MessageType = AgentMessageType | CommandMessageType | 'error';
```

### Python (python/protocol.py)
```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime
from uuid import UUID

class Message(BaseModel):
    id: str
    type: str
    timestamp: datetime
    payload: dict
    signature: str

class HeartbeatPayload(BaseModel):
    status: Literal["idle", "busy", "error"]
    uptime_seconds: int
    system: dict
    environments: list[dict]
    active_tasks: list[str]
```

## Rules

### 타입 변경 시
1. **contracts 먼저**: 어떤 모듈이든 공유 타입을 바꿀 때는 contracts를 먼저 변경
2. **양방향 동기화**: TypeScript ↔ Python 타입은 반드시 일치
3. **Breaking change**: 기존 필드 제거/이름 변경 시 버전 올리기 (v1 → v2)
4. **하위 호환**: 새 필드 추가는 optional로 (기존 클라이언트 깨지지 않도록)

### 자동 생성 파일
- `generated/` 디렉토리의 파일은 **절대 수동 편집 금지**
- 수정이 필요하면 OpenAPI 스펙 또는 생성 설정을 변경

### 버전 관리
- package.json의 version을 SemVer로 관리
- API breaking change → major, 새 엔드포인트 → minor, 타입 수정 → patch

## Do NOT
- generated/ 파일 수동 편집
- TypeScript와 Python 타입 불일치 방치
- contracts 업데이트 없이 API 스키마 변경
- optional이 아닌 새 필드 추가 (하위 호환 깨짐)
