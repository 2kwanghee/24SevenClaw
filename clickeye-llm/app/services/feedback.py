"""피드백 저장·조회 서비스 (P2-MVP).

★저장소★: Qdrant 별도 컬렉션(clickeye_feedback). Qdrant 는 벡터가 필수이므로
size=1 더미 벡터([0.0], DOT)로 컬렉션을 만들고 실데이터는 전부 payload 에 둔다
(벡터 검색 불사용 — scroll+Filter 조회 전용).

★격리 원칙★: KB(clickeye_kb)와 동일 — 모든 조회에 delivery_id 필터를 코드에서
강제한다. 교차 딜리버리 유출 불가.

소비자: prompt-evolve 오프라인 배치가 GET /feedback/{delivery_id} 로 끌어가
챔피언 프롬프트 평가 입력으로 사용한다(질문·답변·평가·당시 모델 포함).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient, models

from app.config import settings
from app.schemas import FeedbackCreate, FeedbackItem

logger = structlog.get_logger("clickeye-llm.feedback")

# 벡터 불사용 — qdrant 컬렉션 제약 충족용 1차원 더미. DOT 는 영벡터 허용(COSINE 은
# 정규화 대상이라 부적합).
_DUMMY_VECTOR: list[float] = [0.0]
_SCROLL_PAGE = 256


def _rating_filter(rating: str | None) -> models.Filter | None:
    """rating 만의 필터(전체 조회용). rating 미지정 시 None(무필터)."""
    if rating is None:
        return None
    return models.Filter(
        must=[models.FieldCondition(key="rating", match=models.MatchValue(value=rating))]  # type: ignore[arg-type]
    )


def _feedback_filter(delivery_id: str, rating: str | None = None) -> models.Filter:
    """delivery_id(+선택 rating) 필터. 모든 조회의 격리 게이트."""
    must: list[models.FieldCondition] = [
        models.FieldCondition(
            key="delivery_id", match=models.MatchValue(value=delivery_id)
        )
    ]
    if rating is not None:
        must.append(
            models.FieldCondition(key="rating", match=models.MatchValue(value=rating))
        )
    return models.Filter(must=must)  # type: ignore[arg-type]


async def _ensure_collection(client: AsyncQdrantClient) -> None:
    """피드백 컬렉션이 없으면 생성(멱등). delivery_id/rating 페이로드 인덱스 포함."""
    collection = settings.qdrant_feedback_collection
    if await client.collection_exists(collection):
        return
    await client.create_collection(
        collection_name=collection,
        vectors_config=models.VectorParams(size=1, distance=models.Distance.DOT),
    )
    await client.create_payload_index(
        collection_name=collection,
        field_name="delivery_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    await client.create_payload_index(
        collection_name=collection,
        field_name="rating",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    logger.info("피드백 컬렉션 생성", collection=collection)


async def save_feedback(client: AsyncQdrantClient, body: FeedbackCreate) -> str:
    """피드백 1건 저장. 포인트 ID(uuid4) = feedback_id 반환."""
    await _ensure_collection(client)
    feedback_id = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "delivery_id": body.delivery_id,
        "chat_id": body.chat_id,
        "query": body.query,
        "answer": body.answer,
        "rating": body.rating,
        "comment": body.comment,
        "sources": body.sources or [],
        # 당시 모델 기록 — 미지정 시 현재 스위처블 설정값(프록시는 모델을 모름).
        "model": body.model or settings.llm_model,
        "created_at": datetime.now(UTC).isoformat(),
    }
    await client.upsert(
        collection_name=settings.qdrant_feedback_collection,
        points=[
            models.PointStruct(id=feedback_id, vector=_DUMMY_VECTOR, payload=payload)
        ],
    )
    logger.info(
        "피드백 저장",
        feedback_id=feedback_id,
        delivery_id=body.delivery_id,
        rating=body.rating,
    )
    return feedback_id


async def list_feedback(
    client: AsyncQdrantClient,
    delivery_id: str,
    rating: str | None = None,
    limit: int = 50,
) -> tuple[list[FeedbackItem], int]:
    """딜리버리 피드백 조회(최신순, ★격리 필터 강제★). (items, 일치 총 건수) 반환.

    scroll 은 정렬을 보장하지 않으므로 일치분을 전량 수집 후 created_at 내림차순
    정렬해 limit 만 자른다(피드백 볼륨은 낮다는 전제 — MVP).
    """
    return await _scroll_sorted(client, _feedback_filter(delivery_id, rating), limit)


async def list_feedback_all(
    client: AsyncQdrantClient,
    rating: str | None = None,
    limit: int = 200,
) -> tuple[list[FeedbackItem], int]:
    """전체(딜리버리 무관) 피드백 조회(최신순) — prompt-evolve 배치 소비 전용.

    ★주의★: delivery_id 격리를 우회하는 유일한 경로. 서비스 내부 포트(:8100)
    직결 배치에서만 사용하며, clickeye-api 프록시는 이 엔드포인트를 노출하지 않는다.
    """
    return await _scroll_sorted(client, _rating_filter(rating), limit)


async def _scroll_sorted(
    client: AsyncQdrantClient,
    flt: models.Filter | None,
    limit: int,
) -> tuple[list[FeedbackItem], int]:
    """필터 일치분 전량 scroll → created_at 내림차순 정렬 → limit 절단."""
    collection = settings.qdrant_feedback_collection
    if not await client.collection_exists(collection):
        return [], 0

    collected: list[tuple[str, dict[str, Any]]] = []
    offset: Any = None
    while True:
        records, offset = await client.scroll(
            collection_name=collection,
            scroll_filter=flt,  # delivery 조회 경로에서는 ★격리 강제★ 필터
            limit=_SCROLL_PAGE,
            offset=offset,
            with_payload=True,
        )
        collected.extend((str(r.id), r.payload or {}) for r in records)
        if offset is None:
            break

    collected.sort(key=lambda x: str(x[1].get("created_at", "")), reverse=True)
    items = [
        FeedbackItem(
            feedback_id=point_id,
            delivery_id=str(p.get("delivery_id", "")),
            chat_id=p.get("chat_id"),
            query=str(p.get("query", "")),
            answer=str(p.get("answer", "")),
            rating=str(p.get("rating", "")),
            comment=p.get("comment"),
            sources=list(p.get("sources") or []),
            model=str(p.get("model", "")),
            created_at=str(p.get("created_at", "")),
        )
        for point_id, p in collected[:limit]
    ]
    return items, len(collected)
