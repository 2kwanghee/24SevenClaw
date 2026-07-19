"""Reporter 단위 테스트."""

from unittest.mock import AsyncMock

from agent.reporter import Reporter


async def test_send_status(mock_connection: AsyncMock, reporter: Reporter) -> None:
    await reporter.send_status("task-1", 0.5, "진행 중")

    mock_connection.send.assert_called_once()
    msg = mock_connection.send.call_args[0][0]
    assert msg["type"] == "agent.status"
    assert msg["payload"]["task_id"] == "task-1"
    assert msg["payload"]["progress"] == 0.5


async def test_send_result(mock_connection: AsyncMock, reporter: Reporter) -> None:
    await reporter.send_result("task-2", "completed", "작업 완료")

    mock_connection.send.assert_called_once()
    msg = mock_connection.send.call_args[0][0]
    assert msg["type"] == "agent.result"
    assert msg["payload"]["status"] == "completed"


async def test_send_log(mock_connection: AsyncMock, reporter: Reporter) -> None:
    await reporter.send_log("task-1", "info", "claude", "hello", project_id="p1")

    mock_connection.send.assert_called_once()
    msg = mock_connection.send.call_args[0][0]
    assert msg["type"] == "agent.log"
    assert msg["payload"]["task_id"] == "task-1"
    assert msg["payload"]["level"] == "info"
    assert msg["payload"]["source"] == "claude"
    assert msg["payload"]["message"] == "hello"
    assert msg["payload"]["truncated"] is False
    assert msg["payload"]["project_id"] == "p1"


async def test_send_status_with_extra(
    mock_connection: AsyncMock, reporter: Reporter
) -> None:
    await reporter.send_status("task-3", 1.0, "완료", event="task.completed")

    msg = mock_connection.send.call_args[0][0]
    assert msg["payload"]["event"] == "task.completed"
