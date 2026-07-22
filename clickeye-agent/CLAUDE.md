# Agent Agent — ClickEye Customer Server Agent Development Guide

> 이 파일은 clickeye-agent 모듈 개발 시 Claude Code가 참조하는 전담 가이드입니다.
> 레포 초기화 시 `clickeye-agent/CLAUDE.md`로 복사합니다.

## Tech Stack
- **Language**: Python 3.12+ (type hints 필수)
- **WebSocket**: websockets 라이브러리
- **Docker**: docker-py (Docker SDK for Python)
- **Config**: Pydantic BaseSettings
- **Local DB**: SQLite (aiosqlite) — 로컬 상태 관리용
- **Process**: asyncio 기반 비동기 데몬
- **Linting**: ruff
- **Type Check**: mypy
- **Package Manager**: uv

## Directory Structure
```
agent/
├── main.py                     # 데몬 엔트리포인트
├── config.py                   # 설정 (라이센스 키, 클라우드 URL 등)
├── connection.py               # WebSocket 클라이언트 (Cloud 연결)
├── auth.py                     # Agent 인증/등록
├── dispatcher.py               # 메시지 타입 → 핸들러 라우팅
├── handlers/
│   ├── base.py                 # BaseHandler 인터페이스
│   ├── config_handler.py       # 설정 관리
│   ├── docker_handler.py       # Docker 컨테이너 관리
│   ├── env_handler.py          # 환경 변수 프로비저닝
│   └── runner_handler.py       # 실행/파이프라인 처리
├── reporter.py                 # 상태 보고 (→ Cloud)
├── local_store.py              # SQLite 로컬 상태 관리
└── utils/
    ├── logger.py               # 구조화 로깅
    └── retry.py                # 재시도 유틸리티
```

## Core Concepts

### 1. Agent는 데몬이다
- 고객 서버에서 백그라운드 프로세스로 실행
- systemd 서비스 또는 Docker 컨테이너로 배포
- 항상 Cloud에 연결 유지 (재연결 자동)

### 2. 모든 통신은 Cloud로의 아웃바운드
- Agent → Cloud 방향으로 WebSocket 연결
- 고객 서버에 인바운드 포트 오픈 불필요
- 방화벽 친화적 (HTTPS/443만 사용)

### 3. 고객 데이터는 로컬에만
- 코드, 빌드 결과, Git 데이터 = 고객 서버에만 저장
- Cloud에는 상태 요약만 보고 (파일명 목록, 성공/실패 등)
- 민감 정보(API 키 등)는 절대 Cloud로 전송 금지

## Coding Rules

### Handler 패턴
```python
# handlers/base.py
from abc import ABC, abstractmethod
from typing import Any

class BaseHandler(ABC):
    def __init__(self, config, reporter, local_store):
        self.config = config
        self.reporter = reporter
        self.store = local_store

    @abstractmethod
    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """명령을 처리하고 결과를 반환"""
        ...

    async def report_progress(self, task_id: str, progress: float, message: str):
        """진행 상황을 Cloud로 보고"""
        await self.reporter.send_status(task_id, progress, message)
```

```python
# handlers/docker_handler.py
import docker
from .base import BaseHandler

class DockerHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.from_env()

    async def handle(self, payload: dict) -> dict:
        action = payload["action"]  # create | start | stop | remove
        match action:
            case "create":
                return await self._create_environment(payload)
            case "start":
                return await self._start_environment(payload)
            # ...

    async def _create_environment(self, payload: dict) -> dict:
        project_id = payload["project_id"]
        await self.report_progress(project_id, 0.1, "Docker 이미지 다운로드 중...")
        # ...
```

### Dispatcher 패턴
```python
# dispatcher.py
class Dispatcher:
    def __init__(self):
        self.handlers: dict[str, BaseHandler] = {}

    def register(self, message_type: str, handler: BaseHandler):
        self.handlers[message_type] = handler

    async def dispatch(self, message: dict) -> dict:
        msg_type = message["type"]
        handler = self.handlers.get(msg_type)
        if not handler:
            return {"error": f"Unknown message type: {msg_type}"}
        return await handler.handle(message["payload"])
```

### WebSocket 연결
```python
# connection.py
import websockets
import asyncio
import json

class CloudConnection:
    def __init__(self, config, dispatcher):
        self.config = config
        self.dispatcher = dispatcher
        self.ws = None
        self.reconnect_delay = 1  # 지수 백오프 시작값

    async def connect(self):
        url = f"{self.config.cloud_ws_url}/ws/agent?agent_id={self.config.agent_id}"
        headers = {"Authorization": f"Bearer {self.config.agent_secret}"}
        self.ws = await websockets.connect(url, extra_headers=headers)
        self.reconnect_delay = 1  # 성공 시 리셋

    async def listen(self):
        """메시지 수신 루프 (재연결 포함)"""
        while True:
            try:
                await self.connect()
                async for raw in self.ws:
                    message = json.loads(raw)
                    result = await self.dispatcher.dispatch(message)
                    await self.ws.send(json.dumps(result))
            except websockets.ConnectionClosed:
                await self._reconnect()

    async def _reconnect(self):
        """지수 백오프 재연결"""
        await asyncio.sleep(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, 300)
```

### Reporter 패턴
```python
# reporter.py
class Reporter:
    def __init__(self, connection):
        self.conn = connection

    async def send_status(self, task_id: str, progress: float, message: str):
        await self.conn.send({
            "type": "agent.status",
            "payload": {
                "task_id": task_id,
                "progress": progress,
                "message": message,
            }
        })

    async def send_heartbeat(self, system_info: dict):
        await self.conn.send({
            "type": "agent.heartbeat",
            "payload": system_info,
        })
```

## Testing
- **단위 테스트**: 각 Handler를 독립적으로 테스트 (Docker mock 사용)
- **통합 테스트**: 실제 Docker 연동 테스트 (CI에서는 Docker-in-Docker)
- **WebSocket 테스트**: 테스트 서버로 연결/메시지/재연결 테스트

## Security Rules
- `agent_secret`은 로컬 파일에만 저장 (퍼미션 600)
- 모든 메시지에 HMAC-SHA256 서명 검증
- 고객 API 키(ANTHROPIC_API_KEY 등)는 환경 변수 참조만 (값 전송 금지)
- Docker 소켓 접근은 필요한 최소 권한만
- 로그에 민감 정보 마스킹

## Do NOT
- Cloud에 고객 소스 코드/데이터 전송
- 동기(sync) I/O 사용 (asyncio 기반)
- Docker 소켓을 외부에 노출
- agent_secret을 로그에 출력
- 하드코딩된 Cloud URL (config 사용)
- 재연결 없는 WebSocket 연결
