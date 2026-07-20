"""위치 무관 Runner 태스크 실행 핸들러 (command.run_task, CE-301/항목 I)

데스크탑 러너(구독 시트, 주력)·클라우드 컨테이너(조직 키, 폴백)가 동일 소비하는
RunnerTaskPayload(계약 python/protocol.py:127) 를 실행한다. agent 는 contracts 를
직접 import 하지 않으므로(기존 핸들러 관례) payload 는 raw dict 로 파싱한다.

TODO(P3, 이월): 수주 인테이크 자동화 — modernize finalize/ZIP 직후 러너로
  RunnerTaskPayload(command.run_task) 를 push 하는 배선이 이 핸들러의 진입점이 된다.
  설계 노트: docs/si-factory-transition.md P3.
"""

import asyncio
import contextlib
from pathlib import Path
from typing import Any

import structlog

from agent.handlers.base import BaseHandler

logger = structlog.get_logger()


async def stream_subprocess(
    *,
    argv: list[str],
    cwd: str | None,
    env: dict[str, str] | None,
    timeout_seconds: float | None,
    reporter: Any,
    task_id: str,
    stream_logs: bool,
    source: str,
    project_id: str = "",
) -> dict[str, Any]:
    """서브프로세스를 async 로 실행하고 stdout 라인을 실시간 스트리밍한다.

    `orchestrator.py:invoke_agent` 의 subprocess.run 패턴을 asyncio 로 이식한 것.
    RunnerHandler 와 DockerHandler(_run/_build) 가 공유한다(중복 회피).

    반환: {"returncode": int, "timed_out": bool, "lines": list[str]}.
    타임아웃 시에도 그때까지 수집한 lines 를 보존한다(클로저 캡처 리스트).

    테스트 seam: 오직 `asyncio.create_subprocess_exec` 만 모킹한다.
    """
    lines: list[str] = []
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def _consume() -> None:
        if proc.stdout is not None:
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip("\r\n")
                lines.append(line)
                if stream_logs:
                    await reporter.send_log(
                        task_id, "info", source, line, project_id=project_id
                    )
        await proc.wait()

    if timeout_seconds:
        try:
            await asyncio.wait_for(_consume(), timeout_seconds)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            logger.warning("서브프로세스 타임아웃", argv=argv, timeout=timeout_seconds)
            return {"returncode": -1, "timed_out": True, "lines": lines}
    else:
        await _consume()

    rc = proc.returncode if proc.returncode is not None else 0
    return {"returncode": rc, "timed_out": False, "lines": lines}


class RunnerHandler(BaseHandler):
    """RunnerTaskPayload 를 실행하고 로그/결과를 스트리밍한다."""

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        task_id = payload.get("task_id", "")
        project_id = payload.get("project_id", "")
        target = payload.get("target")
        auth_mode = payload.get("auth_mode")
        ticket_id = payload.get("ticket_id")
        prompt = payload.get("prompt")
        command = payload.get("command")
        streaming = payload.get("streaming")
        timeout_seconds = payload.get("timeout_seconds")

        logger.info(
            "run_task 수신",
            task_id=task_id,
            project_id=project_id,
            target=target,
            auth_mode=auth_mode,
        )

        # 실행 지시 검증(계약 model_validator "최소 1" 미러). no-op 태스크를 값싸게 방어.
        if not (ticket_id or prompt or command):
            return self._result(
                task_id,
                "failed",
                "실행 지시(ticket_id/prompt/command) 없음",
                target,
                auth_mode,
                rc=-1,
                timed_out=False,
            )

        # 커맨드 도출(우선순위: command > prompt > ticket_id).
        if command:
            argv = ["/bin/sh", "-c", command]
        elif prompt:
            # TODO(P3): 구독 세션 CLI 경로를 config 로 노출(현재 "claude" 리터럴).
            argv = ["claude", "-p", prompt]
        else:
            argv = ["claude", "-p", f"티켓 {ticket_id} 처리"]

        # streaming.logs 기본 true, 명시적 False 일 때만 끈다.
        stream_logs = True
        if isinstance(streaming, dict) and streaming.get("logs") is False:
            stream_logs = False

        # 작업공간: data_dir/workspaces/<project_id> 존재 시 cwd, 없으면 현재 디렉토리.
        # TODO(P3, 이월): 실제 워크스페이스 프로비저닝/관리(clone/unzip) 이월.
        cwd: str | None = None
        workspace = Path(self.config.data_dir) / "workspaces" / project_id
        if project_id and workspace.exists():
            cwd = str(workspace)

        try:
            res = await stream_subprocess(
                argv=argv,
                cwd=cwd,
                env=None,
                timeout_seconds=timeout_seconds,
                reporter=self.reporter,
                task_id=task_id,
                stream_logs=stream_logs,
                source="claude",
                project_id=project_id,
            )
        except Exception as e:  # noqa: BLE001 — 어떤 실행 실패도 failed 결과로 보고
            logger.exception("run_task 실행 실패", task_id=task_id)
            return self._result(
                task_id, "failed", f"실행 실패: {e}", target, auth_mode, rc=-1, timed_out=False
            )

        rc = res["returncode"]
        timed_out = res["timed_out"]
        if timed_out:
            status, summary = "failed", f"타임아웃({timeout_seconds}s) 초과로 중단"
        elif rc != 0:
            status, summary = "failed", f"실행 실패 (exit {rc})"
        else:
            status, summary = "completed", "실행 완료"

        return self._result(
            task_id, status, summary, target, auth_mode, rc=rc, timed_out=timed_out
        )

    def _result(
        self,
        task_id: str,
        status: str,
        summary: str,
        target: str | None,
        auth_mode: str | None,
        *,
        rc: int,
        timed_out: bool,
    ) -> dict[str, Any]:
        """agent.result 봉투를 구성해 반환한다.

        전송은 하지 않는다 — connection.listen 이 반환 dict 를 1회 전송하는 것이
        코드베이스 지배 패턴(EnvHandler/ConfigHandler/DockerHandler)이다. 여기서
        reporter.send_result 를 함께 부르면 result 가 중복 전송된다(CE-301 회계 결함).
        CE-301 회계 필드(target/auth_mode/metrics)는 payload 에 그대로 보존한다.
        """
        metrics = {"returncode": rc, "timed_out": timed_out}
        return {
            "type": "agent.result",
            "payload": {
                "task_id": task_id,
                "status": status,
                "summary": summary,
                "target": target,
                "auth_mode": auth_mode,
                "metrics": metrics,
            },
        }
