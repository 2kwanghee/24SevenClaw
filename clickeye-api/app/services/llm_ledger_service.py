"""LLM 사용량 원장 기록/조회 서비스 (CE-299)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select

from app.models.llm_usage_ledger import (
    LlmKeySource,
    LlmProvider,
    LlmUsageLedger,
    LlmUsageStatus,
)
from app.schemas.llm_ledger import (
    LlmKeySourceTotals,
    LlmProjectUsageSummary,
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
        meta: dict[str, Any] | None = None,
    ) -> LlmUsageLedger:
        """원장 1행을 저장하고 refresh 된 ORM 객체를 반환한다."""
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
            meta=meta,
        )
        await self.save(entry)
        return entry

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

        total = await self.db.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        total = int(total or 0)

        page_stmt = (
            stmt.order_by(LlmUsageLedger.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(page_stmt)
        return list(result.scalars().all()), total

    async def summary_by_project(
        self, project_id: UUID | None
    ) -> LlmProjectUsageSummary:
        """프로젝트별 토큰/비용 합계를 key_source 구분해 집계한다.

        DB 함수 의존을 피하기 위해 행을 로드해 파이썬에서 합산한다(원장 로깅 범위이므로
        규모가 크지 않다). 비용은 조직키 행에만 존재하므로 None 을 건너뛰고 합산한다.
        """
        stmt = select(LlmUsageLedger).where(
            LlmUsageLedger.project_id == project_id
        )
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())

        buckets: dict[str, dict[str, Any]] = {}
        total_in = 0
        total_out = 0
        total_cost: Decimal | None = None

        for row in rows:
            ks = row.key_source.value if hasattr(row.key_source, "value") else str(
                row.key_source
            )
            bucket = buckets.setdefault(
                ks, {"input": 0, "output": 0, "cost": None}
            )
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
