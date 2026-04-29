"""프리셋 설정 동적 수신 핸들러

Cloud에서 config.update 메시지를 수신하여 로컬 SQLite에 저장하고
리로드 시그널을 발행한다.
"""

import asyncio
from typing import Any

import structlog

from agent.handlers.base import BaseHandler

logger = structlog.get_logger()

# 프리셋 설정에 포함될 수 있는 최상위 키
_PRESET_KEYS = frozenset({
    "agents",
    "skills",
    "pipelines",
    "metadata",
})


class ConfigHandler(BaseHandler):
    """config.update 메시지 핸들러.

    payload 예시::

        {
            "preset_id": "uuid-...",
            "preset_slug": "advanced-fullstack",
            "agents": ["claude-code", "gemini-cli"],
            "skills": ["tdd", "lint"],
            "pipelines": ["ci-basic"],
            "metadata": { ... }
        }
    """

    def __init__(self, *args: Any, reload_event: asyncio.Event | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._reload_event = reload_event or asyncio.Event()

    @property
    def reload_event(self) -> asyncio.Event:
        return self._reload_event

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        preset_id = payload.get("preset_id", "")
        preset_slug = payload.get("preset_slug", "unknown")

        logger.info("프리셋 설정 업데이트 수신", preset_id=preset_id, slug=preset_slug)

        # 1. 프리셋 메타 저장
        await self.store.put_config("preset.active_id", preset_id)
        await self.store.put_config("preset.active_slug", preset_slug)

        # 2. 개별 설정 항목 저장
        for key in _PRESET_KEYS:
            if key in payload:
                await self.store.put_config(f"preset.{key}", payload[key])

        # 3. 전체 원본도 보관 (디버깅/감사용)
        await self.store.put_config("preset.raw", payload)

        logger.info("프리셋 설정 로컬 저장 완료", preset_id=preset_id)

        # 4. 리로드 시그널 발행
        self._reload_event.set()
        logger.info("리로드 시그널 발행", preset_id=preset_id)

        return {
            "type": "agent.result",
            "payload": {
                "task_id": preset_id,
                "status": "completed",
                "summary": f"프리셋 '{preset_slug}' 설정 적용 완료",
            },
        }
