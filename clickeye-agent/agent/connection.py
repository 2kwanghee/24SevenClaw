"""Cloud WebSocket 연결 관리"""

import asyncio
import json
from typing import Any

import structlog
import websockets
from websockets.asyncio.client import ClientConnection

from agent.config import AgentSettings
from agent.dispatcher import Dispatcher

logger = structlog.get_logger()


class CloudConnection:
    def __init__(self, config: AgentSettings, dispatcher: Dispatcher):
        self.config = config
        self.dispatcher = dispatcher
        self.ws: ClientConnection | None = None
        self._reconnect_delay = 1.0

    async def connect(self) -> None:
        url = f"{self.config.cloud_ws_url}/ws/agent?agent_id={self.config.agent_id}"
        headers = {"Authorization": f"Bearer {self.config.agent_secret}"}

        self.ws = await websockets.connect(url, additional_headers=headers)
        self._reconnect_delay = 1.0  # 성공 시 리셋
        logger.info("Cloud 연결 성공", url=self.config.cloud_ws_url)

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
