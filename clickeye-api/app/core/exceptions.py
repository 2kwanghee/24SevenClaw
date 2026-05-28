from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

    @classmethod
    def from_key(cls, code: str, locale: str = "ko", status_code: int = 400) -> "AppError":
        """i18n 레지스트리에서 메시지를 조회해 AppError를 생성한다.

        새 발생 케이스에서 opt-in으로 사용한다.
        admin 엔드포인트는 locale="ko"를 직접 전달하면 항상 한국어 응답을 유지한다.
        """
        from app.i18n.error_messages import get_message

        return cls(code=code, message=get_message(code, locale), status_code=status_code)


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "app_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        path=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "unhandled_error",
        request_id=request_id,
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "서버 내부 오류가 발생했습니다.",
            "code": "INTERNAL_ERROR",
        },
    )
