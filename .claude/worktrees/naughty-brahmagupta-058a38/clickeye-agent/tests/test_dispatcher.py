"""Dispatcher 단위 테스트."""

import pytest

from agent.dispatcher import Dispatcher
from tests.conftest import StubHandler


@pytest.fixture
def dispatcher_with_handler(dispatcher: Dispatcher) -> tuple[Dispatcher, StubHandler]:
    handler = StubHandler(result={"type": "response", "payload": {"ok": True}})
    dispatcher.register("test.command", handler)  # type: ignore[arg-type]
    return dispatcher, handler


async def test_dispatch_known_type(
    dispatcher_with_handler: tuple[Dispatcher, StubHandler],
) -> None:
    dispatcher, handler = dispatcher_with_handler
    result = await dispatcher.dispatch({
        "id": "msg-1",
        "type": "test.command",
        "payload": {"key": "value"},
    })
    assert handler.called_with == {"key": "value"}
    assert result is not None
    assert result["type"] == "response"


async def test_dispatch_unknown_type(dispatcher: Dispatcher) -> None:
    result = await dispatcher.dispatch({
        "id": "msg-2",
        "type": "unknown.type",
        "payload": {},
    })
    assert result is not None
    assert result["type"] == "error"
    assert result["payload"]["code"] == "UNKNOWN_MESSAGE_TYPE"


async def test_dispatch_handler_error(dispatcher: Dispatcher) -> None:
    """핸들러 예외 시 에러 응답 반환."""

    class ErrorHandler:
        async def handle(self, payload: dict) -> None:  # type: ignore[type-arg]
            raise RuntimeError("테스트 에러")

    dispatcher.register("error.command", ErrorHandler())  # type: ignore[arg-type]
    result = await dispatcher.dispatch({
        "id": "msg-3",
        "type": "error.command",
        "payload": {},
    })
    assert result is not None
    assert result["payload"]["code"] == "HANDLER_ERROR"
    assert result["payload"]["recoverable"] is True
