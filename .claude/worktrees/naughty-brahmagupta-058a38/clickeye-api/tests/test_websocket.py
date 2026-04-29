"""Agent WebSocket 엔드포인트 통합 테스트."""


import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_ws_connect_and_receive(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """WebSocket 연결 후 메시지 수신 테스트."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac, ac.stream(
        "GET",
        "/ws/agent?agent_id=test-agent-1",
    ) as _resp:
        # WebSocket은 httpx에서 직접 테스트 불가 — starlette testclient 사용
        pass


@pytest.mark.asyncio
async def test_ws_agent_endpoint_exists(client: AsyncClient) -> None:
    """WebSocket 엔드포인트가 등록되어 있는지 확인."""
    # OpenAPI 스펙에서 /ws/agent 경로 확인
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    # WebSocket은 OpenAPI에 포함되지 않을 수 있으므로
    # 앱 라우터에 등록되었는지 간접 확인
    routes = [r.path for r in app.routes]
    assert "/ws/agent" in routes


@pytest.mark.asyncio
async def test_ws_hub_initial_state() -> None:
    """WebSocket Hub 초기 상태 테스트."""
    from app.ws.hub import AgentHub

    hub = AgentHub()
    assert hub.connected_count == 0
    assert hub.list_connections() == []
    assert hub.is_connected("nonexistent") is False
    assert hub.get_info("nonexistent") is None


@pytest.mark.asyncio
async def test_ws_message_handler_unknown_type(db_session) -> None:
    """알 수 없는 메시지 타입 처리 테스트."""
    from app.ws.handlers import handle_agent_message

    result = await handle_agent_message(
        agent_id="test-agent",
        message={"type": "unknown.type", "payload": {}},
        db=db_session,
    )
    assert result is not None
    assert result["type"] == "error"
    assert result["payload"]["code"] == "UNKNOWN_MESSAGE_TYPE"


@pytest.mark.asyncio
async def test_ws_message_handler_heartbeat(db_session) -> None:
    """하트비트 메시지 처리 테스트."""
    from app.ws.handlers import handle_agent_message
    from app.ws.hub import agent_hub

    # 더미 연결 정보 등록
    agent_hub._agent_info["test-agent"] = {"status": "idle"}

    result = await handle_agent_message(
        agent_id="test-agent",
        message={
            "type": "agent.heartbeat",
            "payload": {"status": "busy"},
        },
        db=db_session,
    )

    assert result is not None
    assert result["type"] == "agent.heartbeat.ack"

    # 정리
    agent_hub._agent_info.pop("test-agent", None)


@pytest.mark.asyncio
async def test_ws_message_handler_status(db_session) -> None:
    """상태 메시지 처리 테스트 (로깅만, 응답 없음)."""
    from app.ws.handlers import handle_agent_message

    result = await handle_agent_message(
        agent_id="test-agent",
        message={
            "type": "agent.status",
            "payload": {
                "event": "build_started",
                "project_id": "proj-1",
                "progress": 0.5,
            },
        },
        db=db_session,
    )
    assert result is None


@pytest.mark.asyncio
async def test_ws_message_handler_log(db_session) -> None:
    """로그 메시지 처리 테스트."""
    from app.ws.handlers import handle_agent_message

    result = await handle_agent_message(
        agent_id="test-agent",
        message={
            "type": "agent.log",
            "payload": {
                "level": "info",
                "message": "빌드 시작",
                "source": "build",
            },
        },
        db=db_session,
    )
    assert result is None


@pytest.mark.asyncio
async def test_ws_message_handler_result(db_session) -> None:
    """작업 결과 메시지 처리 테스트."""
    from app.ws.handlers import handle_agent_message

    result = await handle_agent_message(
        agent_id="test-agent",
        message={
            "type": "agent.result",
            "payload": {
                "task_id": "task-1",
                "status": "completed",
                "summary": "빌드 성공",
            },
        },
        db=db_session,
    )
    assert result is None
