"""Qdrant 벡터 KB 클라이언트 — 딜리버리 단위 격리 강제.

★격리 원칙★: 단일 컬렉션(clickeye_kb) + payload.delivery_id.
검색/스크롤은 **항상** delivery_id 필터를 건다 → 교차 딜리버리 유출 불가.
필터를 코드 경로에서 강제(옵션 아님)하여 실수로도 새지 않게 한다.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient, models

logger = structlog.get_logger("clickeye-llm.qdrant")

# UUID5 네임스페이스(고정) — (delivery_id, source_id, chunk_index) → 결정적 포인트 ID.
# 동일 source_id 재수집 시 같은 ID 로 덮어써 증분 갱신을 가능하게 한다.
_ID_NAMESPACE = uuid.UUID("6f1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d")


def _point_id(delivery_id: str, source_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, f"{delivery_id}::{source_id}::{chunk_index}"))


def _delivery_filter(delivery_id: str, source_id: str | None = None) -> models.Filter:
    """delivery_id(+선택 source_id) 필터. 모든 조회의 격리 게이트."""
    must: list[models.FieldCondition] = [
        models.FieldCondition(
            key="delivery_id", match=models.MatchValue(value=delivery_id)
        )
    ]
    if source_id is not None:
        must.append(
            models.FieldCondition(
                key="source_id", match=models.MatchValue(value=source_id)
            )
        )
    return models.Filter(must=must)  # type: ignore[arg-type]


class QdrantKB:
    """네임스페이스 격리 upsert/search/scroll 을 제공하는 래퍼."""

    def __init__(
        self,
        url: str,
        collection: str,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        self._collection = collection
        self._own_client = client is None
        self._client = client or AsyncQdrantClient(url=url)
        self._ensured_dim: int | None = None

    @property
    def client(self) -> AsyncQdrantClient:
        """저수준 공유 클라이언트 — 피드백 등 KB 외 컬렉션 접근용(연결 재사용)."""
        return self._client

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.close()

    async def ensure_collection(self, dim: int) -> None:
        """컬렉션이 없으면 벡터 차원 dim 으로 최초 1회 생성(멱등)."""
        if self._ensured_dim == dim:
            return
        exists = await self._client.collection_exists(self._collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=dim, distance=models.Distance.COSINE
                ),
            )
            # delivery_id 로 자주 필터링 → 페이로드 인덱스 생성(격리 필터 성능).
            await self._client.create_payload_index(
                collection_name=self._collection,
                field_name="delivery_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.info("컬렉션 생성", collection=self._collection, dim=dim)
        self._ensured_dim = dim

    async def upsert(
        self,
        delivery_id: str,
        source_id: str,
        chunks: list[str],
        vectors: list[list[float]],
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """(delivery_id, source_id) 청크 upsert. 증분: 기존 source_id 선삭제 후 재삽입."""
        if not chunks:
            return 0
        await self.ensure_collection(len(vectors[0]))
        # 증분 갱신: 청크 개수가 줄어드는 경우까지 안전하게, 해당 source 를 먼저 비운다.
        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=_delivery_filter(delivery_id, source_id)
            ),
        )
        points = [
            models.PointStruct(
                id=_point_id(delivery_id, source_id, i),
                vector=vectors[i],
                payload={
                    "delivery_id": delivery_id,
                    "source_id": source_id,
                    "chunk_index": i,
                    "text": chunks[i],
                    "metadata": metadata or {},
                },
            )
            for i in range(len(chunks))
        ]
        await self._client.upsert(collection_name=self._collection, points=points)
        return len(points)

    async def search(
        self, delivery_id: str, vector: list[float], top_k: int
    ) -> list[dict[str, Any]]:
        """delivery_id 로 격리된 벡터 검색. 각 히트의 payload+score 반환."""
        if not await self._client.collection_exists(self._collection):
            return []
        result = await self._client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=_delivery_filter(delivery_id),  # ★격리 강제★
            limit=top_k,
            with_payload=True,
        )
        return [
            {**(p.payload or {}), "score": p.score} for p in result.points
        ]

    async def scroll_recent(
        self, delivery_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """진행요약용: 해당 딜리버리 축적 지식을 스크롤로 수집(격리 필터)."""
        if not await self._client.collection_exists(self._collection):
            return []
        records, _ = await self._client.scroll(
            collection_name=self._collection,
            scroll_filter=_delivery_filter(delivery_id),  # ★격리 강제★
            limit=limit,
            with_payload=True,
        )
        return [r.payload or {} for r in records]
