"""거버넌스 게이트 서비스 — SSOT 커널 위임 + (opt-in) 예산 축 원장 접점.

검증/위험분류/트리아지 로직은 저장소 루트 stdlib 전용 커널 `governance.core` 에 단일
존재하고, 여기서는 그 evaluate() 를 호출만 한다(로직 0줄). 유일한 예외는 **DB↔커널
접점**: 트리아지 예산(budget) 축이 opt-in 으로 켜지고 project_id 가 주어지면
LlmLedgerService 로 프로젝트 usage 를 구성해 커널에 주입한다(정직한 한계: 구독시트는
비용 NULL → 예산 skip, 예산 집행은 org_api_key 경로에서 활성).

DB 세션은 **optional 주입**이다. 미주입(현행 DB-less 경로)이면 원장 조회를 건너뛰어
usage=None → 예산 skip(하위호환). 원격 HTTP 는 git/.ralph 미접근이므로 project_dir=None
으로 넘겨 plan-trace 는 skip(비블로킹)되고 files+head(+plan_text)로만 평가한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.schemas.governance import GovernanceEvaluateRequest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class GovernanceGateService:
    def __init__(self, db: AsyncSession | None = None) -> None:
        # DB-less(현행) 경로 보존: db 미주입 시 원장 조회 없이 커널만 호출.
        self.db = db

    async def evaluate(self, req: GovernanceEvaluateRequest) -> dict[str, Any]:
        # 커널은 저장소 루트 패키지 → clickeye-governance 의존성(editable)으로 import 가능.
        from governance.core import evaluate as kernel_evaluate
        from governance.core import is_opt_in

        usage = req.usage
        # usage 직접 주입이 우선. 없고 project_id + 예산 opt-in + DB 세션이 있을 때만
        # 원장을 조회해 usage 를 구성한다(그 외에는 usage=None → 예산 skip).
        if (
            usage is None
            and req.project_id is not None
            and self.db is not None
            and is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET")
        ):
            usage = await self._usage_from_ledger(req.project_id)

        # 원격 HTTP 는 git 이 없을 수 있고 접근해서도 안 된다. files 미지정(None)이면
        # 커널이 os.getcwd() 에서 git diff 를 시도하므로 빈 목록으로 강제(git 미접근 불변식).
        return kernel_evaluate(
            base=req.base,
            head=req.head,
            files=req.files or [],
            project_dir=None,
            plan_text=req.plan_text,
            usage=usage,
            metrics=req.metrics,
        )

    def get_policy(self) -> dict[str, Any]:
        """전역 머지-게이트 정책 요약을 커널에서 읽어 반환한다(읽기 전용, DB 미사용).

        로직은 커널 policy_summary() 에 단일 존재하고 여기서는 위임만 한다(이중관리 0).
        """
        from governance.core import policy_summary

        return policy_summary()

    async def _usage_from_ledger(self, project_id: Any) -> dict[str, Any]:
        """원장 집계 → 커널 usage 계약({cost: float|None, tokens: int})으로 정규화.

        커널은 stdlib 전용(Decimal 미취급)이므로 비용을 float 로 변환한다. 구독시트만 있는
        프로젝트는 total_cost=None → 예산 비용 축은 자연 skip(정당).
        """
        from app.services.llm_ledger_service import LlmLedgerService

        # 호출부(evaluate)가 self.db is not None 을 이미 보장 → 여기서 타입 좁힘.
        assert self.db is not None
        summary = await LlmLedgerService(self.db).summary_by_project(project_id)
        cost = float(summary.total_cost) if summary.total_cost is not None else None
        tokens = summary.total_input_tokens + summary.total_output_tokens
        return {"cost": cost, "tokens": tokens}
