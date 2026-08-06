"""관측 화면(관측 C) 집계 응답 스키마 (CE-388) — 전부 읽기 전용.

빈 데이터에서도 500 을 내지 않도록 모든 집계 필드는 기본값(0 / 빈 컬렉션)을 가진다.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.seat_quota import SeatQuotaLatestEntry

UsageGroupBy = Literal["project_id", "seat_id", "model", "request_kind"]


class DailyOutcome(BaseModel):
    """일자(UTC) 1개에 대한 파이프라인 실행 성공/실패 카운트."""

    date: date
    success: int = 0
    failure: int = 0


class ObservabilityDeliveryEventItem(BaseModel):
    """대시보드 최근 딜리버리 이벤트 피드 1건."""

    id: UUID
    intake_id: UUID
    project_id: UUID | None
    event_type: str
    actor_type: str
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ObservabilitySummaryResponse(BaseModel):
    """대시보드 위젯 — 프로덕트 상태·인테이크 깔때기·파이프라인 성공률·딜리버리 피드."""

    projects_by_status: dict[str, int] = Field(default_factory=dict)
    intake_by_status: dict[str, int] = Field(default_factory=dict)
    intake_by_tickets_status: dict[str, int] = Field(default_factory=dict)
    pipeline_run_success_count: int = 0
    pipeline_run_failure_count: int = 0
    pipeline_run_success_rate: float | None = None
    daily_outcomes: list[DailyOutcome] = Field(default_factory=list)
    recent_delivery_events: list[ObservabilityDeliveryEventItem] = Field(default_factory=list)


class UsagePivotBucket(BaseModel):
    """usage 피벗 1축 값에 대한 집계 1행."""

    key: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: Decimal | None = None
    request_count: int = 0


class UsagePivotResponse(BaseModel):
    """사용량 피벗 — 기간 × 축(project_id/seat_id/model/request_kind) 집계."""

    group_by: UsageGroupBy
    buckets: list[UsagePivotBucket] = Field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: Decimal | None = None
    total_request_count: int = 0


class SeatObservabilityEntry(BaseModel):
    """계정 1개 — 최신 window 스냅샷들 + 시트 상태 + 최근 24h 소비."""

    account_email: str
    seat_id: UUID | None
    seat_status: str | None
    windows: list[SeatQuotaLatestEntry] = Field(default_factory=list)
    usage_24h_input_tokens: int = 0
    usage_24h_output_tokens: int = 0


class SeatObservabilityResponse(BaseModel):
    items: list[SeatObservabilityEntry] = Field(default_factory=list)


class ProjectSeatUsage(BaseModel):
    """프로젝트 상세 — seat 1개(또는 seat_id NULL 그룹)에 대한 토큰/비용 합계."""

    seat_id: str | None
    account_email: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: Decimal | None = None


class ProjectSummaryResponse(BaseModel):
    """프로젝트 상세 드릴다운 — ledger 토큰/비용 총합 + seat 별 그룹 + 최초/최근 활동 시각."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: Decimal | None = None
    first_activity_at: datetime | None = None
    last_activity_at: datetime | None = None
    seats: list[ProjectSeatUsage] = Field(default_factory=list)
