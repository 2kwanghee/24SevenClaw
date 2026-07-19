"""agent.register 전송 흐름 테스트 (항목 F).

- 단위: Reporter.send_register 가 RegisterPayload 를 Message<T> 봉투로 감싸
  전송하는지 (mock connection).
- E2E: 인프로세스 websockets 서버를 임의 포트에 띄우고 CloudConnection.connect()
  가 연결 직후 on_connect 훅으로 agent.register 를 실제 소켓으로 1회 전송하는지.
"""

import asyncio
import contextlib
import json
from unittest.mock import AsyncMock

import pytest
import websockets

from agent.config import AGENT_VERSION, AgentSettings
from agent.connection import CloudConnection
from agent.dispatcher import Dispatcher
from agent.reporter import Reporter

CAPS = ["setup_env", "build", "run", "stop", "destroy_env", "config.update"]


async def test_send_register_envelope(
    monkeypatch: pytest.MonkeyPatch, mock_connection: AsyncMock
) -> None:
    """send_register 가 봉투 + RegisterPayload 규약을 지키는지 검증."""
    # registration_token = 연결에 쓴 agent_token 재제시
    monkeypatch.setattr("agent.config.agent_settings.agent_token", "tok-abc")
    # docker 조회는 환경 비의존이 되도록 스텁
    monkeypatch.setattr("agent.reporter._detect_docker_version", lambda: "24.0.7")

    reporter = Reporter(connection=mock_connection)
    await reporter.send_register(CAPS)

    mock_connection.send.assert_called_once()
    msg = mock_connection.send.call_args[0][0]

    # Message<T> 봉투
    assert msg["type"] == "agent.register"
    assert isinstance(msg["id"], str) and msg["id"]
    assert isinstance(msg["timestamp"], str) and msg["timestamp"]
    assert "signature" in msg

    # RegisterPayload
    p = msg["payload"]
    assert p["registration_token"] == "tok-abc"
    assert p["hostname"]  # 비어있지 않은 호스트명
    assert p["os"]
    assert p["docker_version"] == "24.0.7"
    assert p["agent_version"] == AGENT_VERSION
    assert p["capabilities"] == CAPS


async def test_connect_sends_register(
    monkeypatch: pytest.MonkeyPatch, test_settings: AgentSettings
) -> None:
    """connect() 가 연결 직후 on_connect 훅으로 agent.register 를 전송하는지 (E2E)."""
    monkeypatch.setattr("agent.config.agent_settings.agent_token", "test-token-001")
    monkeypatch.setattr("agent.reporter._detect_docker_version", lambda: "")

    received: asyncio.Future[str] = asyncio.get_event_loop().create_future()

    async def handler(ws: websockets.ServerConnection) -> None:
        # 연결 직후 클라이언트가 보내는 첫 메시지(agent.register)를 수신
        raw = await ws.recv()
        if not received.done():
            received.set_result(raw)
        with contextlib.suppress(Exception):
            await ws.wait_closed()

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    test_settings.cloud_ws_url = f"ws://127.0.0.1:{port}"

    conn = CloudConnection(config=test_settings, dispatcher=Dispatcher())
    reporter = Reporter(connection=conn)
    conn.on_connect = lambda: reporter.send_register(CAPS)

    try:
        await conn.connect()
        raw = await asyncio.wait_for(received, timeout=5.0)
        msg = json.loads(raw)
        assert msg["type"] == "agent.register"
        assert msg["payload"]["registration_token"] == "test-token-001"
        assert msg["payload"]["capabilities"] == CAPS
        assert msg["payload"]["agent_version"] == AGENT_VERSION
    finally:
        if conn.ws is not None:
            with contextlib.suppress(Exception):
                await conn.ws.close()
        server.close()
        await server.wait_closed()
