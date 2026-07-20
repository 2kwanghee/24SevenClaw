"""상태 보고 (Agent → Cloud)"""

import asyncio
import platform
import socket
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from agent.config import AGENT_VERSION

if TYPE_CHECKING:
    from agent.connection import CloudConnection

logger = structlog.get_logger()


def _detect_docker_version() -> str:
    """설치된 Docker 데몬 버전을 best-effort 로 조회한다.

    docker-py 미설치·데몬 미기동 등 어떤 실패든 빈 문자열로 폴백한다
    (register 는 필수 흐름이 아니므로 조회 실패가 등록을 막으면 안 된다).
    """
    try:
        import docker  # 지연 import (조회 시점에만 필요)

        version = docker.from_env().version().get("Version", "")
        return str(version)
    except Exception:
        return ""


class Reporter:
    def __init__(self, connection: "CloudConnection"):
        self.conn = connection

    async def send_register(self, capabilities: list[str]) -> None:
        """연결 수립 직후 1회 전송하는 등록 메시지 (agent.register).

        RegisterPayload(계약: contracts/protocol/messages.ts·python/protocol.py)를
        Message<T> 봉투(id/type/timestamp/payload/signature)로 감싸 전송한다.

        registration_token 은 연결 인증에 쓴 agent_token 을 재제시하는 것으로
        (defense-in-depth), 서버는 이 값이 그 연결의 검증된 agent_token 과
        일치하는지 대조한다. 별도 토큰 발급 체계는 도입하지 않는다(CE-300 캐노니컬).
        """
        from agent.config import agent_settings

        payload = {
            "registration_token": agent_settings.agent_token,
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "docker_version": _detect_docker_version(),
            "agent_version": AGENT_VERSION,
            "capabilities": capabilities,
        }
        await self.conn.send(
            {
                "id": str(uuid.uuid4()),
                "type": "agent.register",
                "timestamp": datetime.now(UTC).isoformat(),
                "payload": payload,
                # HMAC 서명은 아직 미구현(전 메시지 공통) — 빈 문자열 플레이스홀더.
                "signature": "",
            }
        )
        logger.info("agent.register 전송", capabilities=capabilities)

    async def send_status(
        self, task_id: str, progress: float, message: str, **extra: Any
    ) -> None:
        await self.conn.send(
            {
                "type": "agent.status",
                "payload": {
                    "task_id": task_id,
                    "progress": progress,
                    "message": message,
                    **extra,
                },
            }
        )

    async def send_result(
        self, task_id: str, status: str, summary: str, **extra: Any
    ) -> None:
        await self.conn.send(
            {
                "type": "agent.result",
                "payload": {
                    "task_id": task_id,
                    "status": status,
                    "summary": summary,
                    **extra,
                },
            }
        )

    async def send_log(
        self,
        task_id: str,
        level: str,
        source: str,
        message: str,
        truncated: bool = False,
        **extra: Any,
    ) -> None:
        """실행 로그 1줄을 Cloud 로 스트리밍(agent.log).

        계약 LogPayload(protocol.py:64 — level/source/message/truncated + project_id)를
        Message<T> 봉투로 감싼다. project_id 등 계약 필드는 **extra 로 흘려보낸다.
        """
        await self.conn.send(
            {
                "type": "agent.log",
                "payload": {
                    "task_id": task_id,
                    "level": level,
                    "source": source,
                    "message": message,
                    "truncated": truncated,
                    **extra,
                },
            }
        )

    async def heartbeat_loop(self, stop_event: asyncio.Event) -> None:
        """주기적 하트비트 전송"""
        from agent.config import agent_settings

        while not stop_event.is_set():
            try:
                await self.conn.send(
                    {
                        "type": "agent.heartbeat",
                        "payload": {
                            "status": "idle",
                            "hostname": platform.node(),
                            "os": f"{platform.system()} {platform.release()}",
                            "agent_version": AGENT_VERSION,
                        },
                    }
                )
            except Exception:
                logger.warning("하트비트 전송 실패")

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=agent_settings.heartbeat_interval,
                )
                break
            except TimeoutError:
                continue
