"""LLM 사용량 원장 스키마 (CE-299) — Pydantic v2."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class LlmUsageEntryResponse(BaseModel):
    id: UUID
    created_at: datetime | None
    project_id: UUID | None
    task_id: str | None
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
