"""관측 화면(관측 C) 집계 서비스 (CE-388) — 전부 읽기 전용, 신규 마이그레이션 0.

`summary`/`usage` 는 기존 테이블(projects/intake_requests/pipeline_run_events/
delivery_events/llm_usage_ledger)을 조회만 한다. `runs`/`seats` 는 여기서 다루지
않는다 — 각각 `PipelineRunService`/`SeatQuotaService` 를 라우터가 그대로 재사용한다
(중복 구현 금지, 도메인 제약 — .ralph/refined/CE-388.md).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, false, func, select

from app.models.delivery_event import DeliveryEvent
from app.models.intake import IntakeRequest
from app.models.llm_usage_ledger import LlmUsageLedger
from app.models.pipeline_run_event import PipelineRunEvent
from app.models.project import Project
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials
from app.schemas.observability import (
    DailyOutcome,
    ObservabilityDeliveryEventItem,
    ObservabilitySummaryResponse,
    ProjectSeatUsage,
    ProjectSummaryResponse,
    UsageGroupBy,
    UsagePivotBucket,
    UsagePivotResponse,
)
from app.services.base import BaseService

_DEFAULT_SUMMARY_DAYS = 7
_DEFAULT_TREND_DAYS = 3
_RECENT_DELIVERY_EVENTS_LIMIT = 20

# run_done.data.outcome 도메인 (scripts/auto_dev_pipeline.sh RUN_OUTCOME) —
# merged/pr/pushed 는 완주, failed 는 게이트 차단, demoted/unknown 은 판정 보류라
# 성공률 분모에서 제외한다(과대/과소 계상 방지 — 이 라우터 한정 판단).
_SUCCESS_OUTCOMES = {"merged", "pr", "pushed"}
_FAILURE_OUTCOMES = {"failed"}

_USAGE_GROUP_COLUMNS: dict[UsageGroupBy, ColumnElement[Any]] = {
    "project_id": LlmUsageLedger.project_id,
    "seat_id": LlmUsageLedger.seat_id,
    "model": LlmUsageLedger.model,
    "request_kind": LlmUsageLedger.request_kind,
}


def _try_parse_uuid(value: str) -> UUID | None:
    """`project_id` 컬럼은 Uuid 타입이라 문자열을 그대로 바인딩하면 백엔드별로
    바인드 프로세서가 깨진다(SQLite: `str` 엔 `.hex` 없음). 형식이 아니면 None —
    호출측이 `false()` 절로 바꿔 빈 결과를 반환한다(500 대신)."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


class ObservabilityService(BaseService):
    async def summary(
        self,
        *,
        days: int = _DEFAULT_SUMMARY_DAYS,
        trend_days: int = _DEFAULT_TREND_DAYS,
    ) -> ObservabilitySummaryResponse:
        """대시보드 위젯 1회 조회 — 결과 0건 조합은 스키마 기본값(0/빈 컬렉션)으로 채운다."""
        projects_by_status = await self._count_group_by(Project.status)
        intake_by_status = await self._count_group_by(IntakeRequest.status)
        intake_by_tickets_status = await self._count_group_by(IntakeRequest.tickets_status)

        since = datetime.now(UTC) - timedelta(days=days)
        outcome_counts = await self._recent_run_outcomes(since)
        success = sum(n for outcome, n in outcome_counts.items() if outcome in _SUCCESS_OUTCOMES)
        failure = sum(n for outcome, n in outcome_counts.items() if outcome in _FAILURE_OUTCOMES)
        rate_denominator = success + failure
        rate = round(success / rate_denominator, 4) if rate_denominator else None

        effective_trend_days = min(trend_days, days)
        daily_outcomes = await self._daily_run_outcomes(since, effective_trend_days)

        recent_events = await self._recent_delivery_events(_RECENT_DELIVERY_EVENTS_LIMIT)

        return ObservabilitySummaryResponse(
            projects_by_status=projects_by_status,
            intake_by_status=intake_by_status,
            intake_by_tickets_status=intake_by_tickets_status,
            pipeline_run_success_count=success,
            pipeline_run_failure_count=failure,
            pipeline_run_success_rate=rate,
            daily_outcomes=daily_outcomes,
            recent_delivery_events=[
                ObservabilityDeliveryEventItem.model_validate(e) for e in recent_events
            ],
        )

    async def usage(
        self,
        *,
        from_: datetime | None,
        to: datetime | None,
        group_by: UsageGroupBy,
        task_id: str | None,
        project_id: str | None = None,
    ) -> UsagePivotResponse:
        """`llm_usage_ledger` 를 기간 필터 + 단일 축 GROUP BY 집계한다.

        `task_id` 지정 시 해당 이슈(프로젝트 상세 드릴다운)로 추가 필터한다.
        `project_id` 지정 시 해당 프로젝트로 추가 필터한다.
        """
        column = _USAGE_GROUP_COLUMNS[group_by]
        stmt = select(
            column.label("key"),
            func.sum(LlmUsageLedger.input_tokens).label("input_tokens"),
            func.sum(LlmUsageLedger.output_tokens).label("output_tokens"),
            func.sum(LlmUsageLedger.cost).label("cost"),
            func.count().label("request_count"),
        )
        if from_ is not None:
            stmt = stmt.where(LlmUsageLedger.created_at >= from_)
        if to is not None:
            stmt = stmt.where(LlmUsageLedger.created_at <= to)
        if task_id is not None:
            stmt = stmt.where(LlmUsageLedger.task_id == task_id)
        if project_id is not None:
            project_uuid = _try_parse_uuid(project_id)
            stmt = stmt.where(
                LlmUsageLedger.project_id == project_uuid if project_uuid else false()
            )
        stmt = stmt.group_by(column)

        rows = (await self.db.execute(stmt)).all()

        buckets = [
            UsagePivotBucket(
                key=str(r.key) if r.key is not None else None,
                input_tokens=int(r.input_tokens or 0),
                output_tokens=int(r.output_tokens or 0),
                cost=r.cost,
                request_count=int(r.request_count or 0),
            )
            for r in rows
        ]
        costs = [b.cost for b in buckets if b.cost is not None]

        return UsagePivotResponse(
            group_by=group_by,
            buckets=buckets,
            total_input_tokens=sum(b.input_tokens for b in buckets),
            total_output_tokens=sum(b.output_tokens for b in buckets),
            total_cost=sum(costs, Decimal("0")) if costs else None,
            total_request_count=sum(b.request_count for b in buckets),
        )

    async def project_summary(self, project_id: str) -> ProjectSummaryResponse:
        """프로젝트 상세 드릴다운 — ledger 토큰/비용 합계 + seat 별 그룹 + 최초/최근 활동 시각.

        `project_id` 가 존재하지 않거나 UUID 형식이 아니어도 500 대신 빈 집계
        (0/None/빈 리스트)를 반환한다(관측 라우터 전역 컨벤션 — 빈 데이터에 500 을 내지 않음).
        """
        project_uuid = _try_parse_uuid(project_id)
        ledger_match = LlmUsageLedger.project_id == project_uuid if project_uuid else false()
        run_event_match = PipelineRunEvent.project_id == project_uuid if project_uuid else false()

        totals_stmt = select(
            func.sum(LlmUsageLedger.input_tokens).label("input_tokens"),
            func.sum(LlmUsageLedger.output_tokens).label("output_tokens"),
            func.sum(LlmUsageLedger.cost).label("cost"),
            func.min(LlmUsageLedger.created_at).label("first_at"),
            func.max(LlmUsageLedger.created_at).label("last_at"),
        ).where(ledger_match)
        totals_row = (await self.db.execute(totals_stmt)).one()

        run_events_stmt = select(
            func.min(PipelineRunEvent.created_at).label("first_at"),
            func.max(PipelineRunEvent.created_at).label("last_at"),
        ).where(run_event_match)
        run_events_row = (await self.db.execute(run_events_stmt)).one()

        first_candidates = [t for t in (totals_row.first_at, run_events_row.first_at) if t]
        last_candidates = [t for t in (totals_row.last_at, run_events_row.last_at) if t]

        seats_stmt = (
            select(
                LlmUsageLedger.seat_id,
                User.email.label("account_email"),
                func.sum(LlmUsageLedger.input_tokens).label("input_tokens"),
                func.sum(LlmUsageLedger.output_tokens).label("output_tokens"),
                func.sum(LlmUsageLedger.cost).label("cost"),
            )
            .outerjoin(
                UserAnthropicCredentials, UserAnthropicCredentials.id == LlmUsageLedger.seat_id
            )
            .outerjoin(User, User.id == UserAnthropicCredentials.user_id)
            .where(ledger_match)
            .group_by(LlmUsageLedger.seat_id, User.email)
        )
        seat_rows = (await self.db.execute(seats_stmt)).all()

        return ProjectSummaryResponse(
            total_input_tokens=int(totals_row.input_tokens or 0),
            total_output_tokens=int(totals_row.output_tokens or 0),
            total_cost=totals_row.cost,
            first_activity_at=min(first_candidates) if first_candidates else None,
            last_activity_at=max(last_candidates) if last_candidates else None,
            seats=[
                ProjectSeatUsage(
                    seat_id=str(r.seat_id) if r.seat_id is not None else None,
                    account_email=r.account_email,
                    input_tokens=int(r.input_tokens or 0),
                    output_tokens=int(r.output_tokens or 0),
                    cost=r.cost,
                )
                for r in seat_rows
            ],
        )

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────

    async def _count_group_by(self, column: ColumnElement[Any]) -> dict[str, int]:
        stmt = select(column.label("key"), func.count().label("n")).group_by(column)
        rows = (await self.db.execute(stmt)).all()
        return {str(r.key): int(r.n) for r in rows if r.key is not None}

    async def _recent_run_outcomes(self, since: datetime) -> dict[str, int]:
        stmt = select(PipelineRunEvent.data).where(
            PipelineRunEvent.event == "run_done",
            PipelineRunEvent.created_at >= since,
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        counts: dict[str, int] = defaultdict(int)
        for data in rows:
            outcome = data.get("outcome") if isinstance(data, dict) else None
            if outcome:
                counts[str(outcome)] += 1
        return dict(counts)

    async def _daily_run_outcomes(self, since: datetime, trend_days: int) -> list[DailyOutcome]:
        """`since` 이후 `run_done` 이벤트를 일자별(UTC date)로 success/failure 집계한다.

        빈 데이터에서도 날짜 슬롯을 채우기 위해 오늘(UTC) 포함 최근 `trend_days`일의
        연속 날짜 리스트를 먼저 만든 뒤 실제 카운트를 매핑한다(누락 날짜는 0/0).
        """
        today = datetime.now(UTC).date()
        date_slots = [today - timedelta(days=offset) for offset in range(trend_days - 1, -1, -1)]

        stmt = select(PipelineRunEvent.created_at, PipelineRunEvent.data).where(
            PipelineRunEvent.event == "run_done",
            PipelineRunEvent.created_at >= since,
        )
        rows = (await self.db.execute(stmt)).all()

        counts: dict[date, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        for created_at, data in rows:
            outcome = data.get("outcome") if isinstance(data, dict) else None
            if outcome in _SUCCESS_OUTCOMES:
                counts[created_at.date()]["success"] += 1
            elif outcome in _FAILURE_OUTCOMES:
                counts[created_at.date()]["failure"] += 1

        return [
            DailyOutcome(
                date=day,
                success=counts[day]["success"],
                failure=counts[day]["failure"],
            )
            for day in date_slots
        ]

    async def _recent_delivery_events(self, limit: int) -> list[DeliveryEvent]:
        stmt = select(DeliveryEvent).order_by(DeliveryEvent.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())
