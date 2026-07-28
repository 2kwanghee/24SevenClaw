"""거버넌스 게이트 서비스 — SSOT 커널 위임 + (opt-in) 예산 축 원장 접점.

검증/위험분류/트리아지 로직은 저장소 루트 stdlib 전용 커널 `governance.core` 에 단일
존재하고, 여기서는 그 evaluate() 를 호출만 한다(로직 0줄). 유일한 예외는 **DB↔커널
접점**: 트리아지 예산(budget) 축이 opt-in 으로 켜지고 project_id 가 주어지면
LlmLedgerService 로 프로젝트 usage 를 구성해 커널에 주입한다(정직한 한계: 구독시트는
비용 NULL → 예산 skip, 예산 집행은 org_api_key 경로에서 활성).

DB 세션은 **optional 주입**이다. 미주입(현행 DB-less 경로)이면 원장 조회를 건너뛰어
usage=None → 예산 skip(하위호환). 원격 HTTP 는 git/.ralph 미접근이므로 project_dir=None
으로 넘겨 plan-trace 는 skip(비블로킹)되고 files+head(+plan_text)로만 평가한다.

## 정책 주입(다프로젝트화 P0)

두 번째 DB↔커널 접점: `project_id` 가 주어지면 `DeliveryProfile` 을 조회해
`Policy.from_dict(profile.policy)` 를 커널에 주입한다. 주입된 정책은 static —
서버 프로세스 env 를 조회하지 않으므로 프로젝트 간 토글 누수가 없다.

- `project_id` 미지정 → `policy=None` → 커널 기본 정책(env 재독) = **오늘의 동작 그대로**
- 프로파일 미등록 → 기본 정책 폴백 + `policy_source` 로 그 사실을 응답에 노출(조용한 폴백 금지)
- 정책 JSON 불량 → `PolicyError` 전파(라우터가 422 로 변환).
  기본 정책으로 떨어지지 않는다(fail-closed)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from app.schemas.governance import (
    POLICY_SOURCE_NO_DB,
    POLICY_SOURCE_NO_PROFILE,
    POLICY_SOURCE_PROFILE,
    GovernanceEvaluateRequest,
)

if TYPE_CHECKING:
    from governance.policy import Policy
    from sqlalchemy.ext.asyncio import AsyncSession


class GovernanceGateService:
    def __init__(self, db: AsyncSession | None = None) -> None:
        # DB-less(현행) 경로 보존: db 미주입 시 원장/프로파일 조회 없이 커널만 호출.
        self.db = db

    async def evaluate(self, req: GovernanceEvaluateRequest) -> dict[str, Any]:
        # 커널은 저장소 루트 패키지 → clickeye-governance 의존성(editable)으로 import 가능.
        from governance.core import evaluate as kernel_evaluate
        from governance.policy import Policy

        # 프로젝트 정책 해석(미지정이면 (None, None) → 커널 기본 정책 = 현행 동작).
        # 정책 JSON 불량이면 PolicyError 가 여기서 전파된다(fail-closed).
        policy, policy_source = await self._resolve_policy(req.project_id)
        # 토글 판단도 같은 정책을 경유한다 — Policy.default().opt_in(k) 는 is_opt_in(k) 와
        # 동일하므로 정책 미주입 경로의 동작은 불변이고, 주입 시엔 프로파일 토글이 정본이 된다.
        pol = policy or Policy.default()

        usage = req.usage
        # usage 직접 주입이 우선. 없고 project_id + 예산 opt-in + DB 세션이 있을 때만
        # 원장을 조회해 usage 를 구성한다(그 외에는 usage=None → 예산 skip).
        if (
            usage is None
            and req.project_id is not None
            and self.db is not None
            and pol.opt_in("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET")
        ):
            usage = await self._usage_from_ledger(req.project_id)

        # 원격 HTTP 는 git 이 없을 수 있고 접근해서도 안 된다. files 미지정(None)이면
        # 커널이 os.getcwd() 에서 git diff 를 시도하므로 빈 목록으로 강제(git 미접근 불변식).
        result = kernel_evaluate(
            base=req.base,
            head=req.head,
            files=req.files or [],
            project_dir=None,
            plan_text=req.plan_text,
            usage=usage,
            metrics=req.metrics,
            policy=policy,
        )

        # 어떤 정책이 실제로 적용됐는지 노출(project_id 를 준 경우에만 키가 생긴다 →
        # 미지정 호출자의 응답은 바이트 불변).
        if policy_source is not None:
            result["policy_source"] = policy_source

        # KB 자동 인제스트 (P1.5/P1.6, 토글 off 시 no-op, 비차단). project_id 명시가 우선.
        # P1.6: project_id 미지정 + linear_team_id 가 있으면 team→project 역매핑을 시도해
        # **인제스트 용도로만** 사용한다 — 위 트리아지 예산 축(req.project_id 기반 usage
        # 조회)에는 불개입(기존 로직 불변). 역매핑 실패(0/복수건)면 스킵(오염 방지).
        ingest_project_id = req.project_id
        if ingest_project_id is None and req.linear_team_id and self.db is not None:
            from app.config import settings  # noqa: PLC0415

            if settings.feature_llm_autoingest:  # off 면 DB 조회 자체를 생략(회귀 0)
                from app.services.llm_ingest import resolve_project_by_team  # noqa: PLC0415

                ingest_project_id = await resolve_project_by_team(self.db, req.linear_team_id)

        if ingest_project_id is not None:
            from app.services.llm_ingest import enqueue_ingest  # noqa: PLC0415

            failures = result.get("failures") or []
            enqueue_ingest(
                ingest_project_id,
                source_id=f"governance:{req.head}",
                text=f"[거버넌스 평가] head={req.head} verdict={result.get('verdict')} "
                f"tier={result.get('tier')} merge_decision={result.get('merge_decision')}"
                + (f" — failures: {', '.join(failures)}" if failures else ""),
                metadata={"kind": "governance"},
            )

        return result

    async def get_policy(self, project_id: UUID | None = None) -> dict[str, Any]:
        """머지-게이트 정책 요약을 커널에서 읽어 반환한다(읽기 전용).

        로직은 커널 policy_summary() 에 단일 존재하고 여기서는 위임만 한다(이중관리 0).
        project_id 미지정이면 전역(API 서버 env 기준) 요약 — 기존 동작 그대로이며 DB 를
        조회하지 않는다. 지정하면 해당 프로젝트 정책을 주입한 요약을 반환하고, 무엇이
        적용됐는지 policy_source 로 밝힌다(불량 정책은 PolicyError 전파 → 라우터 422).
        """
        from governance.core import policy_summary

        policy, policy_source = await self._resolve_policy(project_id)
        summary = policy_summary(policy)
        if policy_source is not None:
            summary["policy_source"] = policy_source
        return summary

    async def _resolve_policy(self, project_id: UUID | None) -> tuple[Policy | None, str | None]:
        """project_id → (커널에 넘길 정책, policy_source). 미지정이면 (None, None).

        반환 정책이 None 이면 커널이 기본 정책(env 재독, live)을 쓴다 — 현행 경로.
        policy_source 는 project_id 를 준 경우에만 문자열이며, 폴백을 숨기지 않는다.
        불량 JSON 은 PolicyError 로 전파한다(기본 정책으로 조용히 떨어지지 않음).
        """
        if project_id is None:
            return None, None
        if self.db is None:
            # DB 없이 프로파일을 확인할 방법이 없다 → 폴백하되 그 사실을 노출.
            return None, POLICY_SOURCE_NO_DB

        from governance.policy import Policy
        from sqlalchemy import select

        from app.models.delivery_profile import DeliveryProfile

        result = await self.db.execute(
            select(DeliveryProfile).where(DeliveryProfile.project_id == project_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            return None, POLICY_SOURCE_NO_PROFILE
        # PolicyError 는 잡지 않는다 — fail-closed(라우터가 422 로 변환).
        # cast: 모델이 레거시 `Column(JSON)` 선언이라 mypy 는 인스턴스 접근도 Column[Any]
        # 로 본다(레포 전 모델 공통). 런타임 값은 dict 이며, from_dict 가 형태를 검증한다.
        policy_json = cast("dict[str, Any] | None", profile.policy)
        return Policy.from_dict(policy_json), POLICY_SOURCE_PROFILE

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
