"""인제스트 서비스 — 청킹 → 임베딩 → Qdrant upsert(딜리버리 격리, 증분)."""

from __future__ import annotations

import structlog

from app.clients.ollama import OllamaClient
from app.clients.qdrant import QdrantKB
from app.schemas import Document

logger = structlog.get_logger("clickeye-llm.ingest")


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """간단한 문단/길이 기반 청킹.

    1) 빈 줄(문단) 경계로 우선 분할.
    2) 문단이 chunk_size 를 넘으면 overlap 겹침으로 슬라이딩 분할.
    빈 청크는 제거한다.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            chunks.append(para)
            continue
        # 긴 문단은 길이 기반 슬라이딩 윈도우로 분할.
        step = max(1, chunk_size - overlap)
        for start in range(0, len(para), step):
            piece = para[start : start + chunk_size].strip()
            if piece:
                chunks.append(piece)
            if start + chunk_size >= len(para):
                break
    return chunks


async def ingest_documents(
    ollama: OllamaClient,
    qdrant: QdrantKB,
    delivery_id: str,
    documents: list[Document],
    chunk_size: int,
    overlap: int,
) -> int:
    """문서들을 청킹·임베딩·upsert. 총 upsert 청크 수 반환."""
    total = 0
    for doc in documents:
        chunks = chunk_text(doc.text, chunk_size, overlap)
        if not chunks:
            logger.warning("빈 문서 스킵", source_id=doc.source_id)
            continue
        vectors = await ollama.embed(chunks)
        if len(vectors) != len(chunks):
            raise RuntimeError(
                f"임베딩 개수 불일치: chunks={len(chunks)} vectors={len(vectors)}"
            )
        count = await qdrant.upsert(
            delivery_id=delivery_id,
            source_id=doc.source_id,
            chunks=chunks,
            vectors=vectors,
            metadata=doc.metadata,
        )
        total += count
        logger.info(
            "인제스트", delivery_id=delivery_id, source_id=doc.source_id, chunks=count
        )
    return total
