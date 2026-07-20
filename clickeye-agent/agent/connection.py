"""Cloud WebSocket 연결 관리"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote

import structlog
import websockets
from websockets.asyncio.client import ClientConnection

from agent.config import AgentSettings
from agent.dispatcher import Dispatcher

logger = structlog.get_logger()


class CloudConnection:
    def __init__(
        self,
        config: AgentSettings,
        dispatcher: Dispatcher,
        on_connect: Callable[[], Awaitable[None]] | None = None,
    ):
        self.config = config
        self.dispatcher = dispatcher
        # 연결(및 매 재연결) 성공 직후 실행되는 훅. 항목 F: agent.register 전송에 사용.
        self.on_connect = on_connect
        self.ws: ClientConnection | None = None
        self._reconnect_delay = 1.0

    async def connect(self) -> None:
        # CE-300: 서버는 쿼리 파라미터 agent_id + agent_token 을 필수로 요구한다.
        #   (Bearer 헤더 인증 경로는 제거 — 서버가 읽지 않으므로 혼선 방지)
        #   특수문자를 포함할 수 있어 URL 인코딩한다.
        agent_id = quote(self.config.agent_id, safe="")
        agent_token = quote(self.config.agent_token, safe="")
        url = f"{self.config.cloud_ws_url}/ws/agent?agent_id={agent_id}&agent_token={agent_token}"

        self.ws = await websockets.connect(url)
        self._reconnect_delay = 1.0  # 성공 시 리셋
        logger.info("Cloud 연결 성공", url=self.config.cloud_ws_url)

        # 연결 직후 등록 훅 실행(agent.register 전송). 훅 실패가 수신 루프를
        # 막지 않도록 예외는 로깅만 하고 삼킨다.
        if self.on_connect is not None:
            try:
                await self.on_connect()
            except Exception:
                logger.exception("on_connect 훅 실행 실패")

    async def send(self, message: dict[str, Any]) -> None:
        if self.ws is None:
            logger.warning("WebSocket 미연결 상태에서 전송 시도")
            return
        await self.ws.send(json.dumps(message, default=str))

    async def listen(self, stop_event: asyncio.Event) -> None:
        """메시지 수신 루프 (재연결 포함)"""
        while not stop_event.is_set():
            try:
                await self.connect()
                async for raw in self.ws:  # type: ignore[union-attr]
                    if stop_event.is_set():
                        break
                    message = json.loads(raw)
                    result = await self.dispatcher.dispatch(message)
                    if result:
                        await self.send(result)
            except websockets.ConnectionClosed:
                logger.warning("Cloud 연결 끊김, 재연결 시도...")
                await self._reconnect(stop_event)
            except Exception:
                logger.exception("연결 오류")
                await self._reconnect(stop_event)

    async def _reconnect(self, stop_event: asyncio.Event) -> None:
        """지수 백오프 재연결"""
        if stop_event.is_set():
            return
        logger.info("재연결 대기", delay=self._reconnect_delay)
        await asyncio.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, 300)
