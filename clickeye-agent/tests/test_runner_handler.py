"""RunnerHandler + stream_subprocess 단위 테스트.

실제 claude/셸을 실행하지 않고 `asyncio.create_subprocess_exec` 만 모킹한다.
"""

import asyncio
from typing import Any

import pytest

from agent.config import AgentSettings
from agent.dispatcher import Dispatcher
from agent.handlers.docker_handler import DockerHandler
from agent.handlers.runner_handler import RunnerHandler
from agent.reporter import Reporter

EXEC_TARGET = "agent.handlers.runner_handler.asyncio.create_subprocess_exec"


class _FakeStdout:
    def __init__(self, lines: list[bytes]):
        self._lines = list(lines)

    def __aiter__(self) -> "_FakeStdout":
        return self

    async def __anext__(self) -> bytes:
        if self._lines:
            return self._lines.pop(0)
        raise StopAsyncIteration


class FakeProcess:
    def __init__(
        self,
        lines: tuple[bytes, ...] = (),
        returncode: int = 0,
        wait_delay: float = 0.0,
    ):
        self.stdout = _FakeStdout(list(lines))
        self.returncode = returncode
        self._wait_delay = wait_delay
        self.killed = False

    async def wait(self) -> int:
        if self._wait_delay:
            await asyncio.sleep(self._wait_delay)
        return self.returncode

    def kill(self) -> None:
        self.killed = True


def _patch_exec(
    monkeypatch: pytest.MonkeyPatch, proc: FakeProcess, captured: dict[str, Any]
) -> None:
    async def fake_exec(*argv: str, **kwargs: Any) -> FakeProcess:
        captured["argv"] = list(argv)
        captured["kwargs"] = kwargs
        captured["calls"] = captured.get("calls", 0) + 1
        return proc

    monkeypatch.setattr(EXEC_TARGET, fake_exec)


@pytest.fixture
def runner_handler(test_settings: AgentSettings, reporter: Reporter) -> RunnerHandler:
    return RunnerHandler(config=test_settings, reporter=reporter, local_store=None)


def _logs(mock_connection: Any) -> list[dict[str, Any]]:
    return [
        c.args[0]
        for c in mock_connection.send.call_args_list
        if c.args and c.args[0].get("type") == "agent.log"
    ]


# ── command 경로: 스트리밍 + 완료 ────────────────────────────
async def test_command_streams_logs_and_completes(
    runner_handler: RunnerHandler, mock_connection: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc = FakeProcess(lines=(b"line1\n", b"line2\n"), returncode=0)
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, proc, captured)

    result = await runner_handler.handle(
        {"task_id": "t1", "project_id": "p1", "target": "desktop", "command": "echo hi"}
    )

    assert result is not None
    assert result["payload"]["status"] == "completed"
    assert captured["argv"] == ["/bin/sh", "-c", "echo hi"]
    logs = _logs(mock_connection)
    assert len(logs) == 2
    assert logs[0]["payload"]["message"] == "line1"
    assert logs[0]["payload"]["source"] == "claude"


# ── prompt 경로: claude -p ───────────────────────────────────
async def test_prompt_derives_claude_argv(
    runner_handler: RunnerHandler, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, FakeProcess(returncode=0), captured)

    await runner_handler.handle(
        {"task_id": "t", "project_id": "p", "target": "desktop", "prompt": "do X"}
    )

    assert captured["argv"] == ["claude", "-p", "do X"]


# ── ticket_id 만: 최소 프롬프트 구성 ─────────────────────────
async def test_ticket_only_builds_prompt(
    runner_handler: RunnerHandler, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, FakeProcess(returncode=0), captured)

    await runner_handler.handle(
        {"task_id": "t", "project_id": "p", "target": "desktop", "ticket_id": "CE-1"}
    )

    assert captured["argv"] == ["claude", "-p", "티켓 CE-1 처리"]


# ── 실행 지시 없음: 서브프로세스 미실행 + failed ─────────────
async def test_no_exec_spec_fails_without_subprocess(
    runner_handler: RunnerHandler, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, FakeProcess(returncode=0), captured)

    result = await runner_handler.handle(
        {"task_id": "t", "project_id": "p", "target": "desktop"}
    )

    assert result is not None
    assert result["payload"]["status"] == "failed"
    assert captured.get("calls", 0) == 0


# ── 비정상 종료코드 → failed ─────────────────────────────────
async def test_nonzero_returncode_fails(
    runner_handler: RunnerHandler, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, FakeProcess(lines=(b"boom\n",), returncode=2), captured)

    result = await runner_handler.handle(
        {"task_id": "t", "project_id": "p", "target": "desktop", "command": "false"}
    )

    assert result is not None
    assert result["payload"]["status"] == "failed"
    assert result["payload"]["metrics"]["returncode"] == 2


# ── 타임아웃 → kill + failed ─────────────────────────────────
async def test_timeout_kills_and_fails(
    runner_handler: RunnerHandler, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc = FakeProcess(lines=(b"start\n",), returncode=0, wait_delay=10.0)
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, proc, captured)

    result = await runner_handler.handle(
        {
            "task_id": "t",
            "project_id": "p",
            "target": "desktop",
            "command": "sleep 10",
            "timeout_seconds": 0.05,
        }
    )

    assert result is not None
    assert result["payload"]["status"] == "failed"
    assert "타임아웃" in result["payload"]["summary"]
    assert proc.killed is True


# ── streaming.logs False → send_log 없음, 여전히 완료 ────────
async def test_streaming_logs_disabled(
    runner_handler: RunnerHandler, mock_connection: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_exec(monkeypatch, FakeProcess(lines=(b"a\n", b"b\n"), returncode=0), {})

    result = await runner_handler.handle(
        {
            "task_id": "t",
            "project_id": "p",
            "target": "desktop",
            "command": "echo",
            "streaming": {"logs": False},
        }
    )

    assert result is not None
    assert result["payload"]["status"] == "completed"
    assert _logs(mock_connection) == []


# ── dispatcher 라우팅: command.run_task → RunnerHandler ──────
async def test_dispatch_routes_run_task(
    test_settings: AgentSettings, reporter: Reporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_exec(monkeypatch, FakeProcess(lines=(b"ok\n",), returncode=0), {})
    handler = RunnerHandler(config=test_settings, reporter=reporter, local_store=None)
    d = Dispatcher()
    d.register("command.run_task", handler)

    assert "command.run_task" in d.handlers

    result = await d.dispatch(
        {
            "type": "command.run_task",
            "id": "m1",
            "payload": {
                "task_id": "t",
                "project_id": "p",
                "target": "desktop",
                "command": "echo",
            },
        }
    )

    assert result is not None
    assert result["type"] == "agent.result"
    assert result["payload"]["status"] == "completed"


# ── DockerHandler 계약 정합: RunPayload.command 실행 경로 ────
async def test_docker_run_executes_command(
    test_settings: AgentSettings, reporter: Reporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, FakeProcess(lines=(b"served\n",), returncode=0), captured)
    handler = DockerHandler(config=test_settings, reporter=reporter, local_store=None)

    result = await handler.handle({"project_id": "p", "command": "npm start"})

    assert result is not None
    assert result["payload"]["status"] == "completed"
    assert result["payload"]["event"] == "env.run"
    assert captured["argv"] == ["/bin/sh", "-c", "npm start"]


# ── DockerHandler build_type 필드 추론 → _build ──────────────
async def test_docker_build_field_inference(
    test_settings: AgentSettings, reporter: Reporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    _patch_exec(monkeypatch, FakeProcess(returncode=0), captured)
    handler = DockerHandler(config=test_settings, reporter=reporter, local_store=None)

    result = await handler.handle(
        {"project_id": "p", "build_type": "full", "command": "make"}
    )

    assert result is not None
    assert result["payload"]["event"] == "build.finished"
    assert captured["argv"] == ["/bin/sh", "-c", "make"]


# ── DockerHandler target → _stop (구조화 스텁, no-op 아님) ───
async def test_docker_stop_returns_structured_result(
    test_settings: AgentSettings, reporter: Reporter
) -> None:
    handler = DockerHandler(config=test_settings, reporter=reporter, local_store=None)

    result = await handler.handle({"project_id": "p", "target": "all"})

    assert result is not None
    assert result["payload"]["event"] == "env.stopped"
    assert result["payload"]["status"] == "completed"
