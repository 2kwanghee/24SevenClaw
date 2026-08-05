"""시트 잔량 스냅샷 스키마 (CE-387) — cswap `--list --json`(schemaVersion 1) 계약.

결측 관대 수용: `fiveHour.resetsAt` 등은 pct=0 일 때 필드 자체가 없을 수 있어
`datetime | None = None` 으로 받는다. 서버가 엄격 검증으로 배치 전체를 거부하지
않는다(도메인 제약 — .ralph/refined/CE-387.md).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SeatQuotaFiveHourIn(BaseModel):
    pct: Decimal
    resets_at: datetime | None = Field(default=None, alias="resetsAt")

    model_config = {"populate_by_name": True}


class SeatQuotaSevenDayIn(BaseModel):
    pct: Decimal
    resets_at: datetime | None = Field(default=None, alias="resetsAt")
    expected_pct: Decimal | None = Field(default=None, alias="expectedPct")
    ahead_of_pace: bool | None = Field(default=None, alias="aheadOfPace")
    projected_exhaustion_at: datetime | None = Field(default=None, alias="projectedExhaustionAt")
    will_last_to_reset: bool | None = Field(default=None, alias="willLastToReset")

    model_config = {"populate_by_name": True}


class SeatQuotaScopedIn(BaseModel):
    name: str
    pct: Decimal
    resets_at: datetime | None = Field(default=None, alias="resetsAt")
    expected_pct: Decimal | None = Field(default=None, alias="expectedPct")
    ahead_of_pace: bool | None = Field(default=None, alias="aheadOfPace")
    projected_exhaustion_at: datetime | None = Field(default=None, alias="projectedExhaustionAt")
    will_last_to_reset: bool | None = Field(default=None, alias="willLastToReset")

    model_config = {"populate_by_name": True}


class SeatQuotaUsageIn(BaseModel):
    five_hour: SeatQuotaFiveHourIn = Field(alias="fiveHour")
    seven_day: SeatQuotaSevenDayIn = Field(alias="sevenDay")
    scoped: list[SeatQuotaScopedIn] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class SeatQuotaSnapshotIn(BaseModel):
    """cswap `accounts[]` 원소 1개(계정 1개) 원문 그대로."""

    number: int | None = None
    email: str
    organization_name: str | None = Field(default=None, alias="organizationName")
    organization_uuid: str | None = Field(default=None, alias="organizationUuid")
    active: bool | None = None
    usage_status: str | None = Field(default=None, alias="usageStatus")
    usage_fetched_at: datetime | None = Field(default=None, alias="usageFetchedAt")
    usage: SeatQuotaUsageIn

    model_config = {"populate_by_name": True}


class SeatQuotaSnapshotBatchRequest(BaseModel):
    """cswap `--list --json` 배치 수신 요청 (POST /ops/seat-quota/snapshots)."""

    accounts: list[SeatQuotaSnapshotIn] = Field(default_factory=list)


class SeatQuotaSnapshotResponse(BaseModel):
    """배치 수신 결과 — 생성된 행 수 + 부분 실패(skip) 계정 수."""

    rows_created: int
    accounts_processed: int
    accounts_skipped: int


class SeatQuotaLatestEntry(BaseModel):
    id: UUID
    captured_at: datetime | None
    usage_fetched_at: datetime | None
    account_email: str
    organization_uuid: str | None
    seat_id: UUID | None
    window: str
    scope_name: str | None
    pct: Decimal
    resets_at: datetime | None
    expected_pct: Decimal | None
    ahead_of_pace: bool | None
    projected_exhaustion_at: datetime | None
    will_last_to_reset: bool | None
    raw: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class SeatQuotaLatestResponse(BaseModel):
    items: list[SeatQuotaLatestEntry]
