"""파이프라인 실행 이력 스키마 (CE-363).

인제스트는 **배열 1회 전송**을 받는다 — 파이프라인은 run 1건에 여러 이벤트를 남기므로
건당 왕복을 만들지 않는다. 조회는 화면의 두 진입점(티켓별 스레드 / 프로젝트별 집계)에 맞춘다.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineEventIn(BaseModel):
    """이벤트 1건. 이름·페이로드는 `pipeline_metrics.py` 값을 그대로 받는다."""

    run_id: str = Field(..., min_length=1, max_length=128)
    issue_key: str = Field(..., min_length=1, max_length=64)
    event: str = Field(..., min_length=1, max_length=64)
    project_id: UUID | None = None
    workspace_key: str | None = Field(default=None, max_length=64)
    data: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class PipelineEventsIngestRequest(BaseModel):
    """배치 인제스트 — 한 번에 여러 이벤트."""

    events: list[PipelineEventIn] = Field(..., min_length=1, max_length=200)


class PipelineEventResponse(BaseModel):
    event: str
    data: dict[str, Any]
    occurred_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineRunUsage(BaseModel):
    """그 티켓이 소비한 토큰 — `llm_usage_ledger` 에서 조인해 채운다.

    구독형이므로 **소비량**이며 잔여 한도가 아니다. `ref_cost_usd` 는 청구액이 아닌
    참고 환산값이다(CE-362 규약).
    """

    models: list[str] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    ref_cost_usd: float | None = None


class PipelineRunResponse(BaseModel):
    """실행 1건(run) = 티켓 처리 1회. 단계 이벤트 + 그 티켓의 소비 토큰."""

    run_id: str
    issue_key: str
    project_id: UUID | None
    workspace_key: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_s: int | None
    outcome: str | None
    # intended != actual 실행 모델 불일치 — "model_mismatch" 이벤트 존재 여부로 파생(CE-388).
    model_mismatch: bool = False
    events: list[PipelineEventResponse]
    usage: PipelineRunUsage


class PipelineRunListResponse(BaseModel):
    items: list[PipelineRunResponse]
    total: int
