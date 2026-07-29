"""LLM 사용량 원장 스키마 (CE-299) — Pydantic v2."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.llm_usage_ledger import LlmKeySource


class LlmUsageEntryResponse(BaseModel):
    id: UUID
    created_at: datetime | None
    project_id: UUID | None
    task_id: str | None
    seat_id: UUID | None = None
    session_id: str | None = None
    provider: str
    key_source: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: Decimal | None
    request_kind: str
    status: str
    meta: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class LlmUsageModelEntry(BaseModel):
    """modelUsage 의 모델별 항목 — 비캐시 input/output + 캐시 토큰(로컬 배치 CE-328)."""

    # max_length 는 DB 컬럼 상한(llm_usage_ledger.model = String(64))과 동일하게 두어
    # 초과 값이 pydantic 단계에서 422 로 걸러지게 한다(DataError 로 500 이 되는 것 방지, CE-328).
    model: str = Field(
        ..., min_length=1, max_length=64, description="모델 식별자(예: claude-sonnet-5)."
    )
    input_tokens: int = Field(default=0, ge=0, description="비캐시 입력 토큰.")
    output_tokens: int = Field(default=0, ge=0, description="출력 토큰.")
    cache_read_input_tokens: int = Field(default=0, ge=0, description="캐시 읽기 입력 토큰.")
    cache_creation_input_tokens: int = Field(
        default=0, ge=0, description="캐시 생성 입력 토큰."
    )


class LlmUsageIngestRequest(BaseModel):
    """로컬 배치(claude -p) 사용량 인제스트 요청 (CE-328).

    로컬 usage_ingest 스크립트가 result 이벤트의 modelUsage 를 모델별 항목으로 보낸다.
    seat_id/project_id 미확인 시 NULL 허용(서버가 축 손실을 흡수). 항상 202 비블로킹.
    """

    # session_id/request_kind/task_id 의 max_length 도 DB 컬럼 상한과 동일하게 부여한다
    # (session_id/request_kind = String(64), task_id = String(128)). 초과 시 422 (CE-328).
    session_id: str = Field(
        ..., min_length=1, max_length=64, description="result 이벤트의 session_id."
    )
    request_kind: str = Field(
        default="local_batch_implement",
        min_length=1,
        max_length=64,
        description="출처 구분(예: local_batch_implement).",
    )
    key_source: LlmKeySource = Field(
        default=LlmKeySource.subscription_seat,
        description="apiKeySource='none' → subscription_seat, 그 외 → org_api_key.",
    )
    seat_id: UUID | None = Field(default=None, description="구독 시트 ID(CLICKEYE_SEAT_ID).")
    project_id: UUID | None = Field(default=None, description="프로젝트 ID(CLICKEYE_PROJECT_ID).")
    task_id: str | None = Field(
        default=None, max_length=128, description="태스크 상관키(예: CE-328)."
    )
    models: list[LlmUsageModelEntry] = Field(
        ..., min_length=1, description="modelUsage 모델별 항목(1개 이상)."
    )
    meta: dict[str, Any] | None = Field(
        default=None, description="공유 런 정보(total_cost_usd/num_turns/duration_ms 등)."
    )


class LlmUsageListResponse(BaseModel):
    items: list[LlmUsageEntryResponse]
    total: int


class LlmKeySourceTotals(BaseModel):
    """key_source(구독시트/조직키)별 토큰·비용 합계."""

    key_source: str
    input_tokens: int
    output_tokens: int
    cost: Decimal | None  # 구독시트는 비용 미산정 → None


class LlmProjectUsageSummary(BaseModel):
    """프로젝트별 사용량 집계 — key_source 구분 회계 포함."""

    project_id: UUID | None
    total_input_tokens: int
    total_output_tokens: int
    total_cost: Decimal | None
    by_key_source: list[LlmKeySourceTotals]
