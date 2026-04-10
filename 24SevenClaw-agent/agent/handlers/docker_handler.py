"""Docker 컨테이너 관리 핸들러"""

from typing import Any

import structlog

from agent.handlers.base import BaseHandler

logger = structlog.get_logger()


class DockerHandler(BaseHandler):
    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        action = payload.get("action", "unknown")
        project_id = payload.get("project_id", "")

        logger.info("Docker 명령 수신", action=action, project_id=project_id)

        # TODO: Phase 2에서 실제 Docker SDK 연동 구현
        match action:
            case "create":
                return await self._create(payload)
            case "start":
                return await self._start(payload)
            case "stop":
                return await self._stop(payload)
            case "remove":
                return await self._remove(payload)
            case _:
                logger.warning("알 수 없는 Docker 액션", action=action)
                return None

    async def _create(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = payload["project_id"]
        await self.reporter.send_status(project_id, 0.1, "Docker 환경 생성 중...")
        # TODO: docker-py로 컨테이너 생성
        await self.reporter.send_status(project_id, 1.0, "Docker 환경 생성 완료")
        return {"type": "agent.status", "payload": {"event": "env.created", "project_id": project_id}}

    async def _start(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = payload["project_id"]
        # TODO: 컨테이너 시작
        return {"type": "agent.status", "payload": {"event": "env.started", "project_id": project_id}}

    async def _stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = payload["project_id"]
        # TODO: 컨테이너 중지
        return {"type": "agent.status", "payload": {"event": "env.stopped", "project_id": project_id}}

    async def _remove(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = payload["project_id"]
        # TODO: 컨테이너 삭제
        return {"type": "agent.status", "payload": {"event": "env.destroyed", "project_id": project_id}}
