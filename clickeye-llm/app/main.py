import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api import router as rag_router
from app.clients.ollama import OllamaClient
from app.clients.qdrant import QdrantKB
from app.config import settings

logger = structlog.get_logger("clickeye-llm")


def _setup_logging() -> None:
    """structlog 기반 로깅 초기화 (clickeye-api 관례 미러)."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 수명주기: ollama/qdrant 클라이언트를 1회 생성해 app.state 에 부착."""
    app.state.ollama = OllamaClient(
        base_url=settings.ollama_base_url,
        embed_model=settings.embed_model,
        llm_model=settings.llm_model,
        timeout=settings.ollama_timeout,
    )
    app.state.qdrant = QdrantKB(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
    )
    logger.info(
        "clickeye-llm 기동",
        model=settings.llm_model,
        embed_model=settings.embed_model,
        ollama_base_url=settings.ollama_base_url,
        qdrant_url=settings.qdrant_url,
    )
    try:
        yield
    finally:
        await app.state.ollama.aclose()
        await app.state.qdrant.aclose()


def create_app() -> FastAPI:
    """FastAPI 앱 팩토리.

    /health + RAG 라우터(/ingest, /chat, /progress) 노출.
    클라이언트는 lifespan 에서 생성해 app.state 로 공유(스위처블 config 주입).
    """
    _setup_logging()

    app = FastAPI(
        title="ClickEye LLM",
        description="지식축적형 sLLM 진행 어시스턴트 (스위처블 Ollama + Qdrant RAG)",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(rag_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """헬스 체크. 현재 설정된 스위처블 모델명을 함께 반환한다."""
        return {
            "status": "ok",
            "model": settings.llm_model,
            "embed_model": settings.embed_model,
        }

    return app


app = create_app()
