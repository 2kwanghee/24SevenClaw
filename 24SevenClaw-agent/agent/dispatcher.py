"""메시지 타입 → 핸들러 라우팅"""

from typing import Any

import structlog

from agent.handlers.base import BaseHandler

logger = structlog.get_logger()


class Dispatcher:
    def __init__(self) -> None:
        self.handlers: dict[str, BaseHandler] = {}

    def register(self, message_type: str, handler: BaseHandler) -> None:
        self.handlers[message_type] = handler
        logger.debug("핸들러 등록", type=message_type, handler=handler.__class__.__name__)

    async def dispatch(self, message: dict[str, Any]) -> dict[str, Any] | None:
        msg_type = message.get("type", "")
        msg_id = message.get("id", "unknown")

        handler = self.handlers.get(msg_type)
        if handler is None:
            logger.warning("알 수 없는 메시지 타입", type=msg_type, id=msg_id)
            return {
                "type": "error",
                "payload": {
                    "code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"알 수 없는 메시지 타입: {msg_type}",
                    "original_message_id": msg_id,
                },
            }

        logger.info("메시지 처리 시작", type=msg_type, id=msg_id)
        try:
            result = await handler.handle(message.get("payload", {}))
            logger.info("메시지 처리 완료", type=msg_type, id=msg_id)
            return result
        except Exception as e:
            logger.exception("메시지 처리 실패", type=msg_type, id=msg_id)
            return {
                "type": "error",
                "payload": {
                    "code": "HANDLER_ERROR",
                    "message": str(e),
                    "original_message_id": msg_id,
                    "recoverable": True,
                },
            }
