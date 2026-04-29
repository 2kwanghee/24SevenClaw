"""Agent WebSocket 메시지 핸들러.

Agent로부터 수신한 메시지 타입별 처리 로직.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_connection import AgentConnection
from app.ws.hub import agent_hub

logger = structlog.get_logger(__name__)


async def handle_agent_message(
    agent_id: str,
    message: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Agent 메시지를 타입별로 처리한다."""
    msg_type = message.get("type", "")
    payload = message.get("payload", {})

    match msg_type:
        case "agent.register":
            return await _handle_register(agent_id, payload, db)
        case "agent.heartbeat":
            return await _handle_heartbeat(agent_id, payload, db)
        case "agent.status":
            _handle_status(agent_id, payload)
            return None
        case "agent.log":
            _handle_log(agent_id, payload)
            return None
        case "agent.result":
            _handle_result(agent_id, payload)
            return None
        case _:
            logger.warning("unknown_message_type", agent_id=agent_id, type=msg_type)
            return {
                "type": "error",
                "payload": {
                    "code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"알 수 없는 메시지 타입: {msg_type}",
                },
            }


async def _handle_register(
    agent_id: str,
    payload: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Agent 등록: 연결 메타데이터 업데이트."""
    hostname = payload.get("hostname", "unknown")
    agent_hub.update_heartbeat(agent_id, {"status": "idle"})

    # DB에 연결 상태 업데이트
    await db.execute(
        update(AgentConnection)
        .where(AgentConnection.agent_token == agent_id)
        .values(
            status="connected",
            hostname=hostname,
            connected_at=datetime.now(UTC),
            last_heartbeat_at=datetime.now(UTC),
            metadata_={
                "os": payload.get("os"),
                "agent_version": payload.get("agent_version"),
                "docker_version": payload.get("docker_version"),
                "capabilities": payload.get("capabilities", []),
            },
        )
    )
    await db.commit()

    logger.info("agent_registered", agent_id=agent_id, hostname=hostname)
    return {
        "type": "agent.register.ack",
        "payload": {"status": "ok", "message": "등록 완료"},
    }


async def _handle_heartbeat(
    agent_id: str,
    payload: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """하트비트: 연결 상태 갱신."""
    agent_hub.update_heartbeat(agent_id, payload)

    await db.execute(
        update(AgentConnection)
        .where(AgentConnection.agent_token == agent_id)
        .values(
            last_heartbeat_at=datetime.now(UTC),
            status=payload.get("status", "idle"),
        )
    )
    await db.commit()

    return {
        "type": "agent.heartbeat.ack",
        "payload": {"status": "ok"},
    }


def _handle_status(agent_id: str, payload: dict[str, Any]) -> None:
    """상태 업데이트: 로깅 후 실시간 전달 (추후 Redis Pub/Sub)."""
    logger.info(
        "agent_status",
        agent_id=agent_id,
        status_event=payload.get("event"),
        progress=payload.get("progress"),
        status_message=payload.get("message"),
    )
    return None


def _handle_log(agent_id: str, payload: dict[str, Any]) -> None:
    """로그: 레벨에 맞게 기록."""
    level = payload.get("level", "info")
    log_msg = payload.get("message", "")
    source = payload.get("source", "agent")

    log_method = getattr(logger, level, logger.info)
    log_method(
        "agent_log",
        agent_id=agent_id,
        source=source,
        agent_message=log_msg,
    )
    return None


def _handle_result(agent_id: str, payload: dict[str, Any]) -> None:
    """작업 결과: 저장 및 알림 (추후 구현)."""
    task_id = payload.get("task_id")
    status = payload.get("status")

    logger.info(
        "agent_result",
        agent_id=agent_id,
        task_id=task_id,
        status=status,
    )
    # TODO: 티켓 상태 업데이트, 웹소켓으로 프론트엔드 알림
    return None
