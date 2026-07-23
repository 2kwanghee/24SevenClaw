"""RAG 서비스 — 질의 → 임베딩 → 격리 검색 → 컨텍스트 조립 → 생성.

진행요약(progress)도 축적 지식 기반 RAG 요약으로 처리한다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog

from app.clients.ollama import OllamaClient
from app.clients.qdrant import QdrantKB
from app.config import settings
from app.schemas import Source

logger = structlog.get_logger("clickeye-llm.rag")

# 챗 시스템 프롬프트 내장 기본값 — 챔피언 파일(settings.rag_prompt_path) 부재 시 폴백.
# 정본(진화 대상)은 prompts/rag_system.champion.md (P2-full).
_CHAT_SYSTEM = (
    "당신은 SI 딜리버리 지식 어시스턴트입니다. "
    "아래 '컨텍스트'에 담긴 이 딜리버리의 축적된 지식만 근거로 한국어로 답하세요. "
    "컨텍스트에 없는 내용은 지어내지 말고 '축적된 지식에서 확인할 수 없습니다'라고 답하세요."
)

# mtime 캐시 — 파일 mtime 이 변하면 재로드(스왑 = 배치 승격이 재기동 없이 반영).
# 로드 소스(file/builtin)가 바뀔 때만 1회 로깅(매 요청 로그 스팸 방지).
_prompt_cache: dict[str, Any] = {"mtime": None, "text": None, "source": None}


def _load_system_prompt() -> str:
    """챗 시스템 프롬프트 로드: 챔피언 파일 우선, 없으면 내장 기본값 폴백.

    HTML 주석(<!-- ... -->, 챔피언 헤더·후보 변형 주석)은 제거하고 모델에 전달한다.
    """
    path = Path(settings.rag_prompt_path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        if _prompt_cache["source"] != "builtin":
            logger.info(
                "RAG 시스템 프롬프트 = 내장 기본값(챔피언 파일 없음)", path=str(path)
            )
            _prompt_cache.update(mtime=None, text=_CHAT_SYSTEM, source="builtin")
        return _CHAT_SYSTEM

    if _prompt_cache["source"] != "file" or _prompt_cache["mtime"] != mtime:
        raw = path.read_text(encoding="utf-8")
        text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()
        if not text:  # 주석뿐인 빈 파일 — 안전 폴백
            logger.warning("챔피언 프롬프트 파일이 비어 있음 → 내장 기본값", path=str(path))
            text = _CHAT_SYSTEM
        _prompt_cache.update(mtime=mtime, text=text, source="file")
        logger.info("RAG 시스템 프롬프트 로드(챔피언 파일)", path=str(path), mtime=mtime)
    return str(_prompt_cache["text"])


_PROGRESS_SYSTEM = (
    "당신은 SI 딜리버리 진행상황 요약 어시스턴트입니다. "
    "아래 축적된 지식 항목들을 근거로 현재 진행상황을 한국어로 간결히 요약하세요. "
    "지식에 없는 내용은 추측하지 마세요."
)

# 축적 지식이 전혀 없을 때의 결정적 응답(격리 보장 — sLLM 호출 없이 단락).
_NO_KNOWLEDGE_CHAT = "이 딜리버리에는 아직 축적된 지식이 없어 답변할 수 없습니다."
_NO_KNOWLEDGE_PROGRESS = "아직 지식 없음 — 이 딜리버리에 축적된 정보가 없습니다."


def _build_context(hits: list[dict]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        src = h.get("source_id", "?")
        lines.append(f"[{i}] (출처={src}) {h.get('text', '')}")
    return "\n".join(lines)


async def answer_query(
    ollama: OllamaClient,
    qdrant: QdrantKB,
    delivery_id: str,
    query: str,
    top_k: int,
    prompt_override: str | None = None,
) -> tuple[str, list[Source]]:
    """질의 → 답변 + 출처. 히트 0건이면 sLLM 호출 없이 '모름' 단락(격리 보장).

    prompt_override: ★내부 평가 전용★ — prompt-evolve 배치가 후보 프롬프트를 시험할 때만.
    미지정 시 챔피언 파일(mtime 캐시) 또는 내장 기본값.
    """
    vector = (await ollama.embed([query]))[0]
    hits = await qdrant.search(delivery_id, vector, top_k)
    if not hits:
        return _NO_KNOWLEDGE_CHAT, []

    context = _build_context(hits)
    prompt = f"컨텍스트:\n{context}\n\n질문: {query}\n\n답변:"
    system = prompt_override or _load_system_prompt()
    answer = await ollama.generate(prompt, system=system)

    sources = [
        Source(
            source_id=str(h.get("source_id", "")),
            chunk_index=int(h.get("chunk_index", 0)),
            score=float(h.get("score", 0.0)),
            text=str(h.get("text", "")),
            metadata=h.get("metadata") or {},
        )
        for h in hits
    ]
    return answer, sources


async def summarize_progress(
    ollama: OllamaClient,
    qdrant: QdrantKB,
    delivery_id: str,
    limit: int = 20,
) -> tuple[str, int]:
    """축적 지식 기반 진행요약 + 지식 항목 수. 데이터 없으면 '아직 지식 없음'."""
    items = await qdrant.scroll_recent(delivery_id, limit=limit)
    if not items:
        return _NO_KNOWLEDGE_PROGRESS, 0

    context = "\n".join(
        f"- (출처={it.get('source_id', '?')}) {it.get('text', '')}" for it in items
    )
    prompt = f"축적된 지식 항목:\n{context}\n\n위 내용을 바탕으로 진행상황을 요약해 주세요:"
    summary = await ollama.generate(prompt, system=_PROGRESS_SYSTEM)
    return summary, len(items)
