"""파이프라인 실행 이력 서비스 (CE-363).

무인 파이프라인이 티켓 1건을 처리하며 남기는 단계 이벤트를 서버 원장으로 받아
(멱등 upsert) run 단위로 묶어 조회한다. 소비 토큰은 이 테이블에 복제하지 않고
`llm_usage_ledger` 를 조회 시점에 조인해 채운다(단일 진실 유지).

라우터는 얇게, 이 서비스가 두껍게(프로젝트 관례).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.llm_usage_ledger import LlmUsageLedger
from app.models.pipeline_run_event import PipelineRunEvent
from app.schemas.pipeline_run import (
    PipelineEventIn,
    PipelineEventResponse,
    PipelineRunResponse,
    PipelineRunUsage,
)
from app.services.base import BaseService


class PipelineRunService(BaseService):
    """파이프라인 실행 이벤트 인제스트 + run 단위 조회."""

    async def ingest(self, events: list[PipelineEventIn]) -> int:
        """이벤트 배치를 멱등 upsert 한다. 반환값은 수신 건수.

        `(run_id, event)` 유일 제약(`uq_pipeline_run_event`)으로 재전송·재시도는 같은 행을
        갱신한다. `created_at`(최초 수신 시각)은 갱신 대상에서 제외해 보존한다.

        같은 배치 안에 동일 `(run_id, event)` 가 두 번 오면 PG 가 "한 행을 두 번 갱신"으로
        거부하므로, 마지막 값이 이기도록 배치 내에서 먼저 중복을 접는다.
        """
        if not events:
            return 0

        received = len(events)
        now = datetime.now(UTC)

        # 배치 내 (run_id, event) 중복 접기 — 마지막 값 우선.
        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for e in events:
            deduped[(e.run_id, e.event)] = {
                "id": uuid.uuid4(),
                "run_id": e.run_id,
                "issue_key": e.issue_key,
                "project_id": e.project_id,
                "workspace_key": e.workspace_key,
                "event": e.event,
                "data": e.data or {},
                "occurred_at": e.occurred_at,
                "created_at": now,
            }

        stmt = pg_insert(PipelineRunEvent).values(list(deduped.values()))
        stmt = stmt.on_conflict_do_update(
            constraint="uq_pipeline_run_event",
            set_={
                "data": stmt.excluded.data,
                "occurred_at": stmt.excluded.occurred_at,
                "project_id": stmt.excluded.project_id,
                "workspace_key": stmt.excluded.workspace_key,
                "issue_key": stmt.excluded.issue_key,
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return received

    async def list_runs(
        self,
        *,
        issue_key: str | None = None,
        project_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PipelineRunResponse], int]:
        """run 단위(최신순)로 실행 이력을 조회한다. (페이지, 전체 run 수).

        페이지네이션은 이벤트가 아니라 run 기준이다(group by run_id, order by
        max(created_at) desc). 대상 run 의 이벤트는 한 번의 쿼리로 가져와 메모리에서 묶고
        (N+1 금지), 소비 토큰도 이슈 키들로 한 번에 조인한다.
        """
        # ── run 페이지 선택: group by run_id, 최신 이벤트 순 ──
        grp = select(
            PipelineRunEvent.run_id.label("run_id"),
            func.max(PipelineRunEvent.created_at).label("last_at"),
        )
        if issue_key is not None:
            grp = grp.where(PipelineRunEvent.issue_key == issue_key)
        if project_id is not None:
            grp = grp.where(PipelineRunEvent.project_id == project_id)
        grp = grp.group_by(PipelineRunEvent.run_id)

        total = await self.db.scalar(select(func.count()).select_from(grp.subquery()))
        total = int(total or 0)

        page_stmt = (
            grp.order_by(func.max(PipelineRunEvent.created_at).desc()).limit(limit).offset(offset)
        )
        page_rows = (await self.db.execute(page_stmt)).all()
        run_ids = [r.run_id for r in page_rows]
        if not run_ids:
            return [], total

        # ── 대상 run 들의 이벤트 전체를 한 번에 로드 → 메모리에서 묶는다 ──
        ev_stmt = (
            select(PipelineRunEvent)
            .where(PipelineRunEvent.run_id.in_(run_ids))
            .order_by(PipelineRunEvent.created_at.asc())
        )
        all_events = list((await self.db.execute(ev_stmt)).scalars().all())

        by_run: dict[str, list[PipelineRunEvent]] = defaultdict(list)
        issue_keys: set[str] = set()
        for ev in all_events:
            by_run[str(ev.run_id)].append(ev)
            issue_keys.add(str(ev.issue_key))

        # ── 소비 토큰: 이슈 키들로 원장을 한 번에 조회 → 이슈별 집계 ──
        usage_by_issue = await self._usage_by_issue(issue_keys)

        # 최신순(page_rows 순서) 유지.
        items: list[PipelineRunResponse] = []
        for r in page_rows:
            evs = by_run.get(r.run_id, [])
            items.append(self._build_run(r.run_id, evs, usage_by_issue))
        return items, total

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────

    @staticmethod
    def _ev_time(ev: PipelineRunEvent) -> datetime:
        """이벤트의 관측 시각 — occurred_at 우선, 없으면 created_at."""
        return cast(datetime, ev.occurred_at or ev.created_at)

    @staticmethod
    def _ev_data(ev: PipelineRunEvent) -> dict[str, Any]:
        """이벤트 페이로드를 dict 로 좁힌다(JSONB 컬럼 읽기 — 런타임 dict)."""
        return ev.data if isinstance(ev.data, dict) else {}

    def _build_run(
        self,
        run_id: str,
        events: list[PipelineRunEvent],
        usage_by_issue: dict[str, PipelineRunUsage],
    ) -> PipelineRunResponse:
        """run 1건의 이벤트에서 파생 필드를 계산해 응답을 만든다."""
        ordered = sorted(events, key=self._ev_time)

        # 상관 축은 이벤트에서 취한다(비어 있지 않은 첫 값 우선). ORM 컬럼 읽기는 mypy 상
        # Column 타입이라 응답 스키마(str/UUID)로 좁힌다(런타임 불변).
        issue_key = str(ordered[0].issue_key) if ordered else ""
        project_id = next((e.project_id for e in ordered if e.project_id is not None), None)
        workspace_key = next(
            (e.workspace_key for e in ordered if e.workspace_key is not None), None
        )

        started_at = self._ev_time(ordered[0]) if ordered else None
        ended_at = self._ev_time(ordered[-1]) if ordered else None

        # duration_s: impl_done.data.duration_s(구현 소요, 실질 지표) 우선, 없으면 전체 폭 초.
        duration_s: int | None = None
        by_event = {str(e.event): e for e in ordered}
        impl = by_event.get("impl_done")
        if impl is not None:
            raw = self._ev_data(impl).get("duration_s")
            if isinstance(raw, (int, float)):
                duration_s = int(raw)
        if duration_s is None and started_at is not None and ended_at is not None:
            duration_s = int((ended_at - started_at).total_seconds())

        # outcome: run_done.data.outcome.
        outcome: str | None = None
        run_done = by_event.get("run_done")
        if run_done is not None:
            val = self._ev_data(run_done).get("outcome")
            if val is not None:
                outcome = str(val)

        return PipelineRunResponse(
            run_id=run_id,
            issue_key=issue_key,
            project_id=project_id,
            workspace_key=workspace_key,
            started_at=started_at,
            ended_at=ended_at,
            duration_s=duration_s,
            outcome=outcome,
            model_mismatch="model_mismatch" in by_event,
            events=[PipelineEventResponse.model_validate(e) for e in ordered],
            usage=usage_by_issue.get(issue_key, PipelineRunUsage()),
        )

    async def _usage_by_issue(self, issue_keys: set[str]) -> dict[str, PipelineRunUsage]:
        """이슈 키들(= task_id)로 `llm_usage_ledger` 를 한 번에 조회해 이슈별로 합산한다.

        구독형 전용이라 **소비량** 집계다(잔여 한도 아님). `ref_cost_usd` 는 meta 의
        `total_cost_usd`(참고 환산값) 합계이되, 같은 세션의 여러 모델 행에 같은 값이
        복제돼 있으므로 세션당 1회만 더한다. `cache_read_tokens` 는 모델 행별 값이라
        그대로 합산한다. 원장이 비어 있으면 빈 집계를 돌려준다(실패 아님).
        """
        if not issue_keys:
            return {}

        rows = list(
            (
                await self.db.execute(
                    select(LlmUsageLedger).where(LlmUsageLedger.task_id.in_(issue_keys))
                )
            )
            .scalars()
            .all()
        )

        models: dict[str, set[str]] = defaultdict(set)
        input_tok: dict[str, int] = defaultdict(int)
        output_tok: dict[str, int] = defaultdict(int)
        cache_tok: dict[str, int] = defaultdict(int)
        # 세션당 1회만 비용을 더하기 위한 (issue, session) → cost 맵.
        cost_seen: dict[str, dict[str, float]] = defaultdict(dict)

        for row in rows:
            # ORM 컬럼 읽기는 mypy 상 Column 타입이므로 파이썬 값 타입으로 좁힌다(런타임 불변).
            if row.task_id is None:
                continue
            key = str(row.task_id)
            models[key].add(str(row.model))
            input_tok[key] += int(row.input_tokens or 0)
            output_tok[key] += int(row.output_tokens or 0)

            meta: dict[str, Any] = row.meta if isinstance(row.meta, dict) else {}
            cr = meta.get("cache_read_input_tokens")
            if isinstance(cr, (int, float)):
                cache_tok[key] += int(cr)

            tc = meta.get("total_cost_usd")
            if isinstance(tc, (int, float)):
                # session_id 가 없으면 행 id 로 대체 키를 만들어 중복 접힘을 피한다.
                sess = str(row.session_id) if row.session_id is not None else f"__row_{row.id}"
                cost_seen[key][sess] = float(tc)

        result: dict[str, PipelineRunUsage] = {}
        for key in models:
            costs = cost_seen.get(key, {})
            ref_cost = round(sum(costs.values()), 6) if costs else None
            result[key] = PipelineRunUsage(
                models=sorted(models[key]),
                input_tokens=input_tok[key],
                output_tokens=output_tok[key],
                cache_read_tokens=cache_tok[key],
                ref_cost_usd=ref_cost,
            )
        return result
