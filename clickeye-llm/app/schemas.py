"""API 요청/응답 스키마 (Pydantic v2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Document(BaseModel):
    """인제스트 대상 단일 문서."""

    source_id: str = Field(..., description="출처 식별자. 재수집 시 증분 갱신 키.")
    text: str = Field(..., description="본문 텍스트(청킹 대상).")
    metadata: dict[str, Any] | None = Field(default=None, description="부가 메타(출처/링크 등).")


class IngestRequest(BaseModel):
    delivery_id: str = Field(..., description="딜리버리(조직) 네임스페이스. 격리 키.")
    documents: list[Document] = Field(..., description="주입 문서 목록.")


class IngestResponse(BaseModel):
    delivery_id: str
    documents: int = Field(..., description="처리 문서 수.")
    chunks_upserted: int = Field(..., description="upsert 된 청크(포인트) 총 개수.")


class ChatRequest(BaseModel):
    delivery_id: str = Field(..., description="질의 대상 딜리버리 네임스페이스.")
    query: str = Field(..., description="사용자 질문.")
    top_k: int | None = Field(default=None, description="검색 반환 개수(미지정 시 config 기본).")
    extra_context: str | None = Field(
        default=None,
        description=(
            "확정 사실(권위 컨텍스트). 지정 시 RAG 검색결과보다 우선하여 컨텍스트 최상단에 "
            "'## 확정 사실(우선 신뢰)' 블록으로 주입한다. 조직 챗의 DB 하이브리드(활성 "
            "프로젝트 목록) 등 사실 정확성이 필요한 질의에 사용(CE-312)."
        ),
    )
    prompt_override: str | None = Field(
        default=None,
        description=(
            "★내부 평가 전용★ — prompt-evolve 배치(scripts/llm-prompt-evolve.sh)가 "
            "후보 시스템 프롬프트를 시험할 때만 사용. 지정 시 챔피언 프롬프트 대신 이 값을 "
            "시스템 프롬프트로 사용한다. clickeye-api 프록시는 이 필드를 노출/전달하지 않는다."
        ),
    )


class Source(BaseModel):
    source_id: str
    chunk_index: int
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    chat_id: str = Field(..., description="응답 식별자(uuid4). 피드백 연결 키.")


class ProgressResponse(BaseModel):
    delivery_id: str
    summary: str
    knowledge_items: int = Field(..., description="축적된 지식(청크) 개수.")


# ── 피드백 (P2-MVP: 수집·저장·노출) ──


class FeedbackCreate(BaseModel):
    """챗 답변에 대한 사용자 평가. Qdrant clickeye_feedback 컬렉션에 저장."""

    delivery_id: str = Field(..., description="딜리버리 네임스페이스. 격리 키.")
    chat_id: str | None = Field(default=None, description="평가 대상 /chat 응답의 chat_id.")
    query: str = Field(..., description="당시 사용자 질문.")
    answer: str = Field(..., description="당시 어시스턴트 답변 원문.")
    rating: Literal["up", "down"] = Field(..., description="평가(👍 up / 👎 down).")
    comment: str | None = Field(default=None, description="선택 코멘트(주로 down 사유).")
    sources: list[str] | None = Field(
        default=None, description="답변에 사용된 source_id 목록."
    )
    model: str | None = Field(
        default=None, description="당시 llm_model. 미지정 시 서버가 현재 설정값 기록."
    )


class FeedbackResponse(BaseModel):
    feedback_id: str = Field(..., description="저장된 피드백 포인트 ID(uuid4).")


class FeedbackItem(BaseModel):
    """저장된 피드백 1건 — prompt-evolve 배치 소비용(질문·답변·평가·당시 모델)."""

    feedback_id: str
    delivery_id: str
    chat_id: str | None = None
    query: str
    answer: str
    rating: str
    comment: str | None = None
    sources: list[str] = Field(default_factory=list)
    model: str = ""
    created_at: str = Field(default="", description="저장 시각(ISO 8601, UTC).")


class FeedbackListResponse(BaseModel):
    items: list[FeedbackItem] = Field(default_factory=list, description="최신순.")
    total: int = Field(..., description="필터(delivery_id[+rating]) 일치 총 건수.")
