"""Agent WebSocket 연결 허브.

모든 Agent WebSocket 연결을 관리하고
프로젝트별 Agent에 메시지를 전송한다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class AgentHub:
    """Agent WebSocket 연결을 관리하는 중앙 허브."""

    def __init__(self) -> None:
        # agent_id → WebSocket
        self._connections: dict[str, WebSocket] = {}
        # agent_id → 메타데이터
        self._agent_info: dict[str, dict[str, Any]] = {}

    @property
    def connected_count(self) -> int:
        return len(self._connections)

    def register(self, agent_id: str, ws: WebSocket, info: dict[str, Any] | None = None) -> None:
        """Agent 연결을 등록한다."""
        self._connections[agent_id] = ws
        self._agent_info[agent_id] = {
            "connected_at": datetime.now(UTC).isoformat(),
            **(info or {}),
        }
        logger.info("agent_connected", agent_id=agent_id, total=self.connected_count)

    def unregister(self, agent_id: str) -> None:
        """Agent 연결을 해제한다."""
        self._connections.pop(agent_id, None)
        self._agent_info.pop(agent_id, None)
        logger.info("agent_disconnected", agent_id=agent_id, total=self.connected_count)

    def is_connected(self, agent_id: str) -> bool:
        return agent_id in self._connections

    def get_info(self, agent_id: str) -> dict[str, Any] | None:
        return self._agent_info.get(agent_id)

    async def send_to_agent(self, agent_id: str, message: dict[str, Any]) -> bool:
        """특정 Agent에 메시지를 전송한다."""
        ws = self._connections.get(agent_id)
        if ws is None:
            logger.warning("agent_not_connected", agent_id=agent_id)
            return False

        try:
            await ws.send_text(json.dumps(message, default=str))
            return True
        except Exception:
            logger.exception("send_failed", agent_id=agent_id)
            self.unregister(agent_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> int:
        """모든 연결된 Agent에 메시지를 전송한다."""
        sent = 0
        disconnected: list[str] = []

        for agent_id, ws in self._connections.items():
            try:
                await ws.send_text(json.dumps(message, default=str))
                sent += 1
            except Exception:
                disconnected.append(agent_id)

        for agent_id in disconnected:
            self.unregister(agent_id)

        return sent

    def update_heartbeat(self, agent_id: str, data: dict[str, Any]) -> None:
        """하트비트 데이터를 업데이트한다."""
        info = self._agent_info.get(agent_id)
        if info is not None:
            info["last_heartbeat"] = datetime.now(UTC).isoformat()
            info["status"] = data.get("status", "idle")

    def list_connections(self) -> list[dict[str, Any]]:
        """연결된 모든 Agent 정보를 반환한다."""
        return [
            {"agent_id": aid, **info}
            for aid, info in self._agent_info.items()
        ]


# 싱글턴 인스턴스
agent_hub = AgentHub()
