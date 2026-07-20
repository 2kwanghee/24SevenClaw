"""Docker 컨테이너 관리 핸들러 (command.build/run/stop/destroy_env)

Dispatcher 는 메시지 type 을 버리고 payload 만 핸들러에 전달한다(dispatcher.py:38).
따라서 여기서는 계약 payload 필드로 명령을 판별한다(type 소실 → 필드 추론):
  - BuildPayload : build_type(+command, stream_logs)  → _build
  - RunPayload   : command                            → _run
  - StopPayload  : target                             → _stop
  - destroy_env  : (전용 필드 없음)                    → _destroy
계약 정합(action-unknown no-op 버그 제거): 실행 계열(build/run)은 실제 서브프로세스로
실행하고, 컨테이너 조작(stop/destroy)은 환경 의존이 커 구조화 스텁 + 명확한 TODO 로 둔다.
"""

from typing import Any

import structlog

from agent.handlers.base import BaseHandler
from agent.handlers.runner_handler import stream_subprocess

logger = structlog.get_logger()


class DockerHandler(BaseHandler):
    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        project_id = payload.get("project_id", "")
        logger.info("Docker 명령 수신", project_id=project_id, keys=list(payload.keys()))

        # build_type 을 command 보다 먼저 검사한다(Build 도 command 를 가지므로).
        if "build_type" in payload:
            return await self._build(payload)
        if "command" in payload:
            return await self._run(payload)
        if "target" in payload:
            return await self._stop(payload)
        return await self._destroy(payload)

    async def _build(self, payload: dict[str, Any]) -> dict[str, Any]:
        """BuildPayload.command 를 실행한다.

        TODO(P3, 이월): 실제 docker 이미지/compose 빌드(docker SDK)는 환경 의존이 커
          이번엔 빌드 커맨드의 최소 실동작 실행만 제공한다.
        """
        project_id = payload["project_id"]
        command = payload.get("command", "")
        await self.reporter.send_status(project_id, 0.1, "빌드 실행 중...")
        res = await stream_subprocess(
            argv=["/bin/sh", "-c", command],
            cwd=None,
            env=None,
            timeout_seconds=None,
            reporter=self.reporter,
            task_id=project_id,
            stream_logs=bool(payload.get("stream_logs", False)),
            source="build",
            project_id=project_id,
        )
        status = "completed" if res["returncode"] == 0 else "failed"
        await self.reporter.send_status(project_id, 1.0, f"빌드 {status}")
        return {
            "type": "agent.result",
            "payload": {
                "task_id": project_id,
                "status": status,
                "summary": f"빌드 {status}",
                "event": "build.finished",
                "metrics": {"returncode": res["returncode"]},
            },
        }

    async def _run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """RunPayload.command 를 실행한다(RunnerHandler 와 동일 async 서브프로세스 공유)."""
        project_id = payload["project_id"]
        command = payload.get("command", "")
        res = await stream_subprocess(
            argv=["/bin/sh", "-c", command],
            cwd=None,
            env=None,
            timeout_seconds=None,
            reporter=self.reporter,
            task_id=project_id,
            stream_logs=False,
            source="docker",
            project_id=project_id,
        )
        status = "completed" if res["returncode"] == 0 else "failed"
        return {
            "type": "agent.result",
            "payload": {
                "task_id": project_id,
                "status": status,
                "summary": f"실행 {status}",
                "event": "env.run",
                "metrics": {"returncode": res["returncode"]},
            },
        }

    async def _stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """StopPayload.target 기반 중지.

        TODO(P3, 이월): docker SDK 로 실제 컨테이너 중지(환경 의존). 현재 구조화 스텁.
        """
        project_id = payload["project_id"]
        target = payload.get("target", "all")
        await self.reporter.send_status(project_id, 1.0, f"중지 요청({target})")
        return {
            "type": "agent.result",
            "payload": {
                "task_id": project_id,
                "status": "completed",
                "summary": f"중지({target}) 처리",
                "event": "env.stopped",
            },
        }

    async def _destroy(self, payload: dict[str, Any]) -> dict[str, Any]:
        """환경 삭제(destroy_env).

        TODO(P3, 이월): docker SDK 로 실제 컨테이너/볼륨 삭제(환경 의존). 현재 구조화 스텁.
        """
        project_id = payload.get("project_id", "")
        await self.reporter.send_status(project_id, 1.0, "환경 삭제 요청")
        return {
            "type": "agent.result",
            "payload": {
                "task_id": project_id,
                "status": "completed",
                "summary": "환경 삭제 처리",
                "event": "env.destroyed",
            },
        }
