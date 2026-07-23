"""RAG API 라우터 — /ingest, /chat, /progress, /feedback.

클라이언트(ollama/qdrant)는 앱 lifespan 에서 app.state 에 부착되고,
여기서는 Request 를 통해 참조한다(요청마다 재생성하지 않음).
"""

from __future__ import annotations

import uuid
from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from app.clients.ollama import OllamaClient, OllamaError
from app.clients.qdrant import QdrantKB
from app.config import settings
from app.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackResponse,
    IngestRequest,
    IngestResponse,
    ProgressResponse,
)
from app.services import feedback as feedback_svc
from app.services import ingest as ingest_svc
from app.services import rag as rag_svc

logger = structlog.get_logger("clickeye-llm.api")

router = APIRouter()


def _ollama(request: Request) -> OllamaClient:
    return request.app.state.ollama


def _qdrant(request: Request) -> QdrantKB:
    return request.app.state.qdrant


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: Request, body: IngestRequest) -> IngestResponse:
    """딜리버리 지식 주입: 청킹·임베딩·upsert(증분). upsert 청크 수 반환."""
    if not body.documents:
        raise HTTPException(status_code=400, detail="documents 가 비어 있습니다.")
    try:
        total = await ingest_svc.ingest_documents(
            ollama=_ollama(request),
            qdrant=_qdrant(request),
            delivery_id=body.delivery_id,
            documents=body.documents,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=f"임베딩 백엔드 오류: {exc}") from exc
    return IngestResponse(
        delivery_id=body.delivery_id,
        documents=len(body.documents),
        chunks_upserted=total,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """RAG Q&A: 격리 검색 → 컨텍스트 조립 → 생성. 답변 + 출처 반환."""
    top_k = body.top_k or settings.top_k
    try:
        answer, sources = await rag_svc.answer_query(
            ollama=_ollama(request),
            qdrant=_qdrant(request),
            delivery_id=body.delivery_id,
            query=body.query,
            top_k=top_k,
            # ★내부 평가 전용★ — prompt-evolve 배치만 사용. api 프록시는 미전달.
            prompt_override=body.prompt_override,
            # 확정 사실(권위 컨텍스트, CE-312) — 조직 챗 DB 하이브리드 주입.
            extra_context=body.extra_context,
        )
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 백엔드 오류: {exc}") from exc
    # chat_id: 응답 식별자 — 피드백(POST /feedback)이 어느 응답에 대한 것인지 연결.
    return ChatResponse(answer=answer, sources=sources, chat_id=str(uuid.uuid4()))


@router.get("/progress/{delivery_id}", response_model=ProgressResponse)
async def progress(request: Request, delivery_id: str) -> ProgressResponse:
    """축적 지식 기반 진행요약. 데이터 없으면 '아직 지식 없음'."""
    try:
        summary, count = await rag_svc.summarize_progress(
            ollama=_ollama(request),
            qdrant=_qdrant(request),
            delivery_id=delivery_id,
        )
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=f"LLM 백엔드 오류: {exc}") from exc
    return ProgressResponse(
        delivery_id=delivery_id, summary=summary, knowledge_items=count
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(request: Request, body: FeedbackCreate) -> FeedbackResponse:
    """챗 답변 피드백 저장(P2-MVP). Qdrant clickeye_feedback 컬렉션에 payload 저장."""
    feedback_id = await feedback_svc.save_feedback(_qdrant(request).client, body)
    return FeedbackResponse(feedback_id=feedback_id)


@router.get("/feedback", response_model=FeedbackListResponse)
async def get_feedback_all(
    request: Request,
    rating: Literal["up", "down"] | None = Query(
        default=None, description="평가 필터(up|down). 미지정 시 전체."
    ),
    limit: int = Query(default=200, ge=1, le=1000, description="최신순 반환 개수."),
) -> FeedbackListResponse:
    """전체 피드백 조회(딜리버리 무관, 최신순) — prompt-evolve 배치 소비 전용.

    서비스 내부 포트(:8100) 직결 배치용. clickeye-api 프록시는 미노출(격리 우회 방지).
    """
    items, total = await feedback_svc.list_feedback_all(
        _qdrant(request).client, rating=rating, limit=limit
    )
    return FeedbackListResponse(items=items, total=total)


@router.get("/feedback/{delivery_id}", response_model=FeedbackListResponse)
async def get_feedback(
    request: Request,
    delivery_id: str,
    rating: Literal["up", "down"] | None = Query(
        default=None, description="평가 필터(up|down). 미지정 시 전체."
    ),
    limit: int = Query(default=50, ge=1, le=500, description="최신순 반환 개수."),
) -> FeedbackListResponse:
    """딜리버리 피드백 조회(최신순) — prompt-evolve 배치 소비용. delivery_id 격리."""
    items, total = await feedback_svc.list_feedback(
        _qdrant(request).client, delivery_id=delivery_id, rating=rating, limit=limit
    )
    return FeedbackListResponse(items=items, total=total)
