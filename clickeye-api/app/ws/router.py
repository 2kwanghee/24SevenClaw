"""Agent WebSocket 엔드포인트."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent_connection import AgentConnection
from app.ws.handlers import handle_agent_message
from app.ws.hub import agent_hub

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/agent")
async def agent_websocket(
    ws: WebSocket,
    agent_id: str = Query(...),
    agent_token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Agent WebSocket 연결 엔드포인트.

    Agent가 ?agent_id=xxx&agent_token=yyy 쿼리 파라미터로 인증하여 연결한다.
    """
    # agent_token DB 검증
    stmt = select(AgentConnection).where(AgentConnection.agent_token == agent_token)
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()

    if conn is None:
        await ws.close(code=4001, reason="유효하지 않은 agent_token")
        return

    await ws.accept()
    agent_hub.register(agent_id, ws, info={"project_id": str(conn.project_id)})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(
                    json.dumps({
                        "type": "error",
                        "payload": {"code": "INVALID_JSON", "message": "유효하지 않은 JSON"},
                    })
                )
                continue

            result = await handle_agent_message(agent_id, message, db)
            if result is not None:
                await ws.send_text(json.dumps(result, default=str))

    except WebSocketDisconnect:
        logger.info("agent_ws_disconnect", agent_id=agent_id)
    except Exception:
        logger.exception("agent_ws_error", agent_id=agent_id)
    finally:
        agent_hub.unregister(agent_id)
