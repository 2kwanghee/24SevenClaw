"""관측 화면(관측 C) 집계 서비스 (CE-388) — 전부 읽기 전용, 신규 마이그레이션 0.

`summary`/`usage` 는 기존 테이블(projects/intake_requests/pipeline_run_events/
delivery_events/llm_usage_ledger)을 조회만 한다. `runs`/`seats` 는 여기서 다루지
않는다 — 각각 `PipelineRunService`/`SeatQuotaService` 를 라우터가 그대로 재사용한다
(중복 구현 금지, 도메인 제약 — .ralph/refined/CE-388.md).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select

from app.models.delivery_event import DeliveryEvent
from app.models.intake import IntakeRequest
from app.models.llm_usage_ledger import LlmUsageLedger
from app.models.pipeline_run_event import PipelineRunEvent
from app.models.project import Project
from app.schemas.observability import (
    ObservabilityDeliveryEventItem,
    ObservabilitySummaryResponse,
    UsageGroupBy,
    UsagePivotBucket,
    UsagePivotResponse,
)
from app.services.base import BaseService

_RECENT_DAYS = 7
_RECENT_DELIVERY_EVENTS_LIMIT = 20

# run_done.data.outcome 도메인 (scripts/auto_dev_pipeline.sh RUN_OUTCOME) —
# merged/pr/pushed 는 완주, failed 는 게이트 차단, demoted/unknown 은 판정 보류라
# 성공률 분모에서 제외한다(과대/과소 계상 방지 — 이 라우터 한정 판단).
_SUCCESS_OUTCOMES = {"merged", "pr", "pushed"}
_FAILURE_OUTCOMES = {"failed"}

_USAGE_GROUP_COLUMNS: dict[UsageGroupBy, ColumnElement] = {
    "project_id": LlmUsageLedger.project_id,
    "seat_id": LlmUsageLedger.seat_id,
    "model": LlmUsageLedger.model,
    "request_kind": LlmUsageLedger.request_kind,
}


class ObservabilityService(BaseService):
    async def summary(self) -> ObservabilitySummaryResponse:
        """대시보드 위젯 1회 조회 — 결과 0건 조합은 스키마 기본값(0/빈 컬렉션)으로 채운다."""
        projects_by_status = await self._count_group_by(Project.status)
        intake_by_status = await self._count_group_by(IntakeRequest.status)
        intake_by_tickets_status = await self._count_group_by(IntakeRequest.tickets_status)

        since = datetime.now(UTC) - timedelta(days=_RECENT_DAYS)
        outcome_counts = await self._recent_run_outcomes(since)
        success = sum(n for outcome, n in outcome_counts.items() if outcome in _SUCCESS_OUTCOMES)
        failure = sum(n for outcome, n in outcome_counts.items() if outcome in _FAILURE_OUTCOMES)
        rate_denominator = success + failure
        rate = round(success / rate_denominator, 4) if rate_denominator else None

        recent_events = await self._recent_delivery_events(_RECENT_DELIVERY_EVENTS_LIMIT)

        return ObservabilitySummaryResponse(
            projects_by_status=projects_by_status,
            intake_by_status=intake_by_status,
            intake_by_tickets_status=intake_by_tickets_status,
            pipeline_run_success_count=success,
            pipeline_run_failure_count=failure,
            pipeline_run_success_rate=rate,
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
    ) -> UsagePivotResponse:
        """`llm_usage_ledger` 를 기간 필터 + 단일 축 GROUP BY 집계한다.

        `task_id` 지정 시 해당 이슈(프로젝트 상세 드릴다운)로 추가 필터한다.
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

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────

    async def _count_group_by(self, column: ColumnElement) -> dict[str, int]:
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

    async def _recent_delivery_events(self, limit: int) -> list[DeliveryEvent]:
        stmt = select(DeliveryEvent).order_by(DeliveryEvent.created_at.desc()).limit(limit)
        return list((await self.db.execute(stmt)).scalars().all())
