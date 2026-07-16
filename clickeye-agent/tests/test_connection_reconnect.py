"""CloudConnection 재접속 E2E 테스트 (CE-300).

인프로세스 websockets 테스트 서버를 임의 포트에 띄우고
CloudConnection.listen() 을 태스크로 실행하여
  (a) 첫 연결 수립 시 서버가 agent_id·agent_token 쿼리를 수신하는지,
  (b) 서버가 소켓을 끊으면 클라이언트가 ConnectionClosed 를 잡고 재연결하는지,
  (c) 재연결 성공 후 _reconnect_delay 가 1.0 으로 리셋되는지
를 실제 소켓 통신으로 검증한다.
"""

import asyncio
import contextlib
from urllib.parse import parse_qs, urlparse

import pytest
import websockets

from agent.config import AgentSettings
from agent.connection import CloudConnection
from agent.dispatcher import Dispatcher


@pytest.mark.asyncio
async def test_reconnect_after_server_close(test_settings: AgentSettings) -> None:
    """첫 연결 → 서버 강제 종료 → 자동 재연결 → 백오프 리셋 검증."""
    received_paths: list[str] = []
    second_connected = asyncio.Event()

    async def handler(ws: websockets.ServerConnection) -> None:
        # 클라이언트가 보낸 URL(쿼리 포함)을 기록
        received_paths.append(ws.request.path)
        if len(received_paths) == 1:
            # 첫 연결은 비정상 코드로 끊어 클라이언트의 ConnectionClosed 경로를 유도
            await ws.close(code=1011, reason="테스트 강제 종료")
            return
        # 두 번째(재)연결은 유지 → 재접속 성립 신호
        second_connected.set()
        with contextlib.suppress(Exception):
            await ws.wait_closed()

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    test_settings.cloud_ws_url = f"ws://127.0.0.1:{port}"

    conn = CloudConnection(config=test_settings, dispatcher=Dispatcher())
    # 재연결 대기 시간을 줄여 테스트를 빠르게 (기본 1.0s 백오프 → 0.1s)
    conn._reconnect_delay = 0.1
    stop_event = asyncio.Event()

    listen_task = asyncio.create_task(conn.listen(stop_event))

    try:
        # (b) 재연결이 수립될 때까지 대기
        await asyncio.wait_for(second_connected.wait(), timeout=5.0)

        # (a) 첫 연결과 재연결 모두 agent_id + agent_token 쿼리를 수신했는지 확인
        assert len(received_paths) >= 2
        for path in received_paths[:2]:
            qs = parse_qs(urlparse(path).query)
            assert qs.get("agent_id") == ["test-agent-001"], f"agent_id 누락: {path}"
            assert qs.get("agent_token") == ["test-token-001"], f"agent_token 누락: {path}"

        # (c) 재연결 성공 직후 백오프 지연이 1.0 으로 리셋
        #   서버 핸들러가 클라이언트 connect() 의 리셋 라인보다 먼저 실행될 수 있어
        #   (수립 순서 경합) 리셋이 관측될 때까지 짧게 폴링한다.
        async def _wait_reset() -> None:
            while conn._reconnect_delay != 1.0:
                await asyncio.sleep(0.01)

        await asyncio.wait_for(_wait_reset(), timeout=2.0)
        assert conn._reconnect_delay == 1.0
    finally:
        stop_event.set()
        if conn.ws is not None:
            with contextlib.suppress(Exception):
                await conn.ws.close()
        listen_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listen_task
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_connect_sends_both_query_params(test_settings: AgentSettings) -> None:
    """connect() 가 agent_id 와 agent_token 을 쿼리로 전송하는지 (핸드셰이크 정합)."""
    received_path: asyncio.Future[str] = asyncio.get_event_loop().create_future()

    async def handler(ws: websockets.ServerConnection) -> None:
        if not received_path.done():
            received_path.set_result(ws.request.path)
        with contextlib.suppress(Exception):
            await ws.wait_closed()

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    test_settings.cloud_ws_url = f"ws://127.0.0.1:{port}"

    conn = CloudConnection(config=test_settings, dispatcher=Dispatcher())
    try:
        await conn.connect()
        path = await asyncio.wait_for(received_path, timeout=5.0)
        qs = parse_qs(urlparse(path).query)
        assert qs.get("agent_id") == ["test-agent-001"]
        assert qs.get("agent_token") == ["test-token-001"]
        # 성공 연결이므로 백오프 지연은 1.0
        assert conn._reconnect_delay == 1.0
    finally:
        if conn.ws is not None:
            with contextlib.suppress(Exception):
                await conn.ws.close()
        server.close()
        await server.wait_closed()
