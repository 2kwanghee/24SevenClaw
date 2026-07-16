"""Agent WebSocket 엔드포인트."""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update
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
    # CE-300: canonical 크리덴셜(쿼리로 검증한 agent_token)을 hub info 에도 담아
    #   핸들러/조회에서 재사용한다. (agent_id 는 라우팅 라벨)
    agent_hub.register(
        agent_id,
        ws,
        info={"project_id": str(conn.project_id), "agent_token": agent_token},
    )

    # CE-300: register 메시지(P1, 이번 범위 밖) 없이도 쿼리 인증만으로 상태 전이가
    #   성립하도록 accept 직후 status=connected 로 갱신한다.
    #   (heartbeat 의 last_heartbeat_at 갱신은 핸들러에 그대로 유지)
    #   update() 문 스타일로 갱신하여 검증된 agent_token 으로 정확히 1행만 매칭한다.
    await db.execute(
        update(AgentConnection)
        .where(AgentConnection.agent_token == agent_token)
        .values(status="connected", connected_at=datetime.now(UTC))
    )
    await db.commit()

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

            response = await handle_agent_message(
                agent_id, message, db, agent_token=agent_token
            )
            if response is not None:
                await ws.send_text(json.dumps(response, default=str))

    except WebSocketDisconnect:
        logger.info("agent_ws_disconnect", agent_id=agent_id)
    except Exception:
        logger.exception("agent_ws_error", agent_id=agent_id)
    finally:
        agent_hub.unregister(agent_id)
        # CE-300: 연결 종료 시 status=disconnected 로 되돌린다 (재접속 시 재갱신).
        with contextlib.suppress(Exception):
            await db.execute(
                update(AgentConnection)
                .where(AgentConnection.agent_token == agent_token)
                .values(status="disconnected")
            )
            await db.commit()
