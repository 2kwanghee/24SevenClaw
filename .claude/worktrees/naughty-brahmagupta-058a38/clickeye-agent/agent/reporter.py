"""상태 보고 (Agent → Cloud)"""

import asyncio
import platform
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from agent.connection import CloudConnection

logger = structlog.get_logger()


class Reporter:
    def __init__(self, connection: "CloudConnection"):
        self.conn = connection

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
                            "agent_version": "0.1.0",
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
            except asyncio.TimeoutError:
                continue
