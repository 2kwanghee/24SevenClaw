"""LLM 사용량 원장 기록/조회 서비스 (CE-299)."""

from __future__ import annotations

import contextlib
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.llm_usage_ledger import (
    LlmKeySource,
    LlmProvider,
    LlmUsageLedger,
    LlmUsageStatus,
)
from app.models.user_anthropic_credentials import UserAnthropicCredentials
from app.schemas.llm_ledger import (
    LlmKeySourceTotals,
    LlmProjectUsageSummary,
    LlmUsageIngestRequest,
)
from app.services.base import BaseService


class LlmLedgerService(BaseService):
    """원장 1행 기록 + 프로젝트별 집계 조회.

    TODO(P3, 이월): project_id 상관키로 roi_service 추정치와 조인해 실마진을 산출한다.
      단위 통일(토큰비 vs 인건비 KRW) 설계 선행 필요. docs/si-factory-transition.md P3.
    """

    async def record(
        self,
        *,
        provider: LlmProvider,
        key_source: LlmKeySource,
        model: str,
        request_kind: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: Decimal | None = None,
        status: LlmUsageStatus = LlmUsageStatus.success,
        project_id: UUID | None = None,
        task_id: str | None = None,
        seat_id: UUID | None = None,
        session_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> LlmUsageLedger:
        """원장 1행을 저장하고 refresh 된 ORM 객체를 반환한다.

        seat_id/session_id 는 키워드 전용이며 기본 None 이라 기존 게이트웨이 호출은
        영향을 받지 않는다(로컬 배치 인제스트 CE-328 에서만 전달).
        """
        entry = LlmUsageLedger(
            provider=provider,
            key_source=key_source,
            model=model,
            request_kind=request_kind,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            status=status,
            project_id=project_id,
            task_id=task_id,
            seat_id=seat_id,
            session_id=session_id,
            meta=meta,
        )
        await self.save(entry)
        return entry

    async def _dup_exists(self, session_id: str, model: str) -> bool:
        """(session_id, model) 원장 행이 이미 존재하는지 — 앱 레벨 멱등/중복 확인."""
        dup = await self.db.scalar(
            select(LlmUsageLedger.id).where(
                LlmUsageLedger.session_id == session_id,
                LlmUsageLedger.model == model,
            )
        )
        return dup is not None

    async def record_usage_batch(self, req: LlmUsageIngestRequest) -> dict[str, Any]:
        """로컬 배치(claude -p) 사용량을 modelUsage 모델별 1행으로 원장에 기록한다(CE-328).

        비블로킹 계약(항상 202): 어떤 경로도 예외를 던지지 않고 status dict 를 반환한다.
        - seat_id 사전검증: 미존재 시 seat_id=NULL + meta.unknown_seat_id 에 원값 보존
          (FK 위반 500 방지, 조용한 축 손실 금지).
        - 멱등 2단: ① 앱 레벨 SELECT(session_id, model 존재 시 skip) ② IntegrityError
          방어(부분 유니크 인덱스 race 백스톱, 마이그레이션 057). 실제 중복만 skip 처리하고,
          중복이 아닌 제약 위반(예: INSERT 직전 시트 삭제 → FK 위반)은 seat_id=NULL 로 1회
          재시도하며, 재시도도 실패하면 failed 카운트로 집계한다(조용한 행 손실 금지).
        - 캐시 토큰(cache_read/creation)과 공유 런 정보(요청 meta)는 각 행 meta JSONB 에.
          비용은 v1 에서 산정하지 않는다(cost=NULL, total_cost_usd 는 meta 에만).

        seat 사전검증 SELECT·dup SELECT 를 포함한 배치 전체를 try 로 감싸, 예상치 못한
        SQLAlchemyError(DataError/OperationalError 등)도 라우터로 전파하지 않고
        {'status':'skipped'} 로 흡수한다(202 비블로킹 계약 유지).
        """
        try:
            return await self._record_usage_batch_inner(req)
        except SQLAlchemyError as exc:
            # seat 사전검증/dup SELECT 등에서 발생한 DB 오류 — rollback 후 비블로킹 흡수.
            with contextlib.suppress(SQLAlchemyError):  # rollback 자체 실패는 방어만
                await self.db.rollback()
            return {
                "status": "skipped",
                "reason": f"DB 오류(비블로킹): {type(exc).__name__}",
            }

    async def _record_usage_batch_inner(self, req: LlmUsageIngestRequest) -> dict[str, Any]:
        """record_usage_batch 의 본체 — SQLAlchemyError 는 상위에서 흡수한다."""
        # seat_id 사전검증 — 원장 FK(SET NULL) 위반을 500 이 아닌 축 손실+meta 로 흡수.
        seat_id = req.seat_id
        unknown_seat: str | None = None
        if seat_id is not None:
            exists = await self.db.scalar(
                select(UserAnthropicCredentials.id).where(UserAnthropicCredentials.id == seat_id)
            )
            if exists is None:
                unknown_seat = str(seat_id)
                seat_id = None

        rows = 0
        skipped = 0
        failed = 0
        for m in req.models:
            # ① 앱 레벨 멱등: 동일 (session_id, model) 이미 기록됨 → skip.
            if await self._dup_exists(req.session_id, m.model):
                skipped += 1
                continue

            # 공유 런 정보(요청 meta) + 모델별 캐시 토큰을 행 meta 에 보존.
            row_meta: dict[str, Any] = dict(req.meta or {})
            row_meta["cache_read_input_tokens"] = m.cache_read_input_tokens
            row_meta["cache_creation_input_tokens"] = m.cache_creation_input_tokens
            if unknown_seat is not None:
                row_meta["unknown_seat_id"] = unknown_seat

            try:
                await self.record(
                    provider=LlmProvider.anthropic,
                    key_source=req.key_source,
                    model=m.model,
                    request_kind=req.request_kind,
                    input_tokens=m.input_tokens,
                    output_tokens=m.output_tokens,
                    cost=None,
                    project_id=req.project_id,
                    task_id=req.task_id,
                    seat_id=seat_id,
                    session_id=req.session_id,
                    meta=row_meta,
                )
                rows += 1
            except IntegrityError:
                # ② 제약 위반 — 실제 중복인지 확인해 중복/비중복을 구분한다.
                await self.db.rollback()
                if await self._dup_exists(req.session_id, m.model):
                    # 부분 유니크 인덱스 race(프로덕션) — 실제 중복이므로 skip.
                    skipped += 1
                    continue
                # 중복이 아닌 제약 위반(예: 사전검증 이후 시트 삭제 → FK 위반).
                # seat_id 를 떨어뜨리고 원값을 meta 에 보존해 1회 재시도(조용한 손실 금지).
                retry_meta = dict(row_meta)
                retry_meta["ingest_retry_reason"] = "fk_violation"
                if seat_id is not None:
                    retry_meta["unknown_seat_id"] = str(seat_id)
                try:
                    await self.record(
                        provider=LlmProvider.anthropic,
                        key_source=req.key_source,
                        model=m.model,
                        request_kind=req.request_kind,
                        input_tokens=m.input_tokens,
                        output_tokens=m.output_tokens,
                        cost=None,
                        project_id=req.project_id,
                        task_id=req.task_id,
                        seat_id=None,
                        session_id=req.session_id,
                        meta=retry_meta,
                    )
                    rows += 1
                except SQLAlchemyError:
                    await self.db.rollback()
                    failed += 1
                    continue
            except SQLAlchemyError:
                # 그 외 DB 오류(DataError 등) — rollback 후 실패 카운트(예외 전파 금지).
                await self.db.rollback()
                failed += 1
                continue

        if rows == 0:
            result: dict[str, Any] = {
                "status": "skipped",
                "reason": "중복 session_id(이미 기록됨) 또는 기록할 행 없음",
            }
        else:
            result = {"status": "recorded", "rows": rows}
        if failed:
            result["failed"] = failed
        return result

    async def list_entries(
        self,
        *,
        project_id: UUID | None = None,
        provider: LlmProvider | None = None,
        status: LlmUsageStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[LlmUsageLedger], int]:
        """필터/페이지네이션 조회. (행 목록, 필터 조건 총건수)."""
        stmt = select(LlmUsageLedger)
        if project_id is not None:
            stmt = stmt.where(LlmUsageLedger.project_id == project_id)
        if provider is not None:
            stmt = stmt.where(LlmUsageLedger.provider == provider)
        if status is not None:
            stmt = stmt.where(LlmUsageLedger.status == status)

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        total = int(total or 0)

        page_stmt = stmt.order_by(LlmUsageLedger.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(page_stmt)
        return list(result.scalars().all()), total

    async def summary_by_project(self, project_id: UUID | None) -> LlmProjectUsageSummary:
        """프로젝트별 토큰/비용 합계를 key_source 구분해 집계한다.

        DB 함수 의존을 피하기 위해 행을 로드해 파이썬에서 합산한다(원장 로깅 범위이므로
        규모가 크지 않다). 비용은 조직키 행에만 존재하므로 None 을 건너뛰고 합산한다.
        """
        stmt = select(LlmUsageLedger).where(LlmUsageLedger.project_id == project_id)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())

        buckets: dict[str, dict[str, Any]] = {}
        total_in = 0
        total_out = 0
        total_cost: Decimal | None = None

        for row in rows:
            ks = row.key_source.value if hasattr(row.key_source, "value") else str(row.key_source)
            bucket = buckets.setdefault(ks, {"input": 0, "output": 0, "cost": None})
            # ORM 컬럼 읽기는 mypy 상 Column 타입이므로 파이썬 값 타입으로 좁힌다(런타임 불변).
            in_tok = int(row.input_tokens or 0)
            out_tok = int(row.output_tokens or 0)
            bucket["input"] += in_tok
            bucket["output"] += out_tok
            total_in += in_tok
            total_out += out_tok
            if row.cost is not None:
                row_cost = cast(Decimal, row.cost)
                bucket["cost"] = (bucket["cost"] or Decimal("0")) + row_cost
                total_cost = (total_cost or Decimal("0")) + row_cost

        by_key_source = [
            LlmKeySourceTotals(
                key_source=ks,
                input_tokens=b["input"],
                output_tokens=b["output"],
                cost=b["cost"],
            )
            for ks, b in sorted(buckets.items())
        ]

        return LlmProjectUsageSummary(
            project_id=project_id,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_cost=total_cost,
            by_key_source=by_key_source,
        )
