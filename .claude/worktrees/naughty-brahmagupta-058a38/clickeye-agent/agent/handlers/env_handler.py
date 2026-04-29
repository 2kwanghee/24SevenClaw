"""환경 프로비저닝 핸들러"""

from typing import Any

import structlog

from agent.handlers.base import BaseHandler

logger = structlog.get_logger()


class EnvHandler(BaseHandler):
    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        project_id = payload.get("project_id", "")
        project_name = payload.get("project_name", "unknown")

        logger.info("환경 프로비저닝 시작", project_id=project_id, name=project_name)

        await self.reporter.send_status(project_id, 0.0, "환경 프로비저닝 시작...")

        # TODO: Phase 2에서 실제 구현
        # 1. 환경 템플릿 로드
        # 2. Docker 이미지 pull
        # 3. 컨테이너 생성 + 시작
        # 4. Claude 설치 + 구성
        # 5. Git 저장소 초기화

        await self.reporter.send_status(project_id, 1.0, "환경 프로비저닝 완료")

        return {
            "type": "agent.result",
            "payload": {
                "task_id": project_id,
                "status": "completed",
                "summary": f"프로젝트 '{project_name}' 환경 프로비저닝 완료",
            },
        }
