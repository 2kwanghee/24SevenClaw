from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.exceptions import AppError, app_exception_handler, unhandled_exception_handler
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.redis import close_redis, init_redis
from app.ws.router import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 시작 시 초기화
    setup_logging()
    await init_redis()
    yield
    # 종료 시 정리
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ClickEye API",
        description="AI 에이전트 개발 오케스트레이션 플랫폼",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 미들웨어 (역순으로 실행됨 — 아래가 먼저)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # 예외 핸들러
    app.add_exception_handler(AppError, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 라우터
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(ws_router)

    return app


app = create_app()
