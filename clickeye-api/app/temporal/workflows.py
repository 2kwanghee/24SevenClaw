"""Temporal 워크플로 정의 (CE-296 스켈레톤 + CE-297 P1 섀도우).

- HealthCheckWorkflow: 워커 기동·연결 검증용 최소 워크플로(CE-296).
- ShadowDeliveryWorkflow: 거버넌스 결정을 미러링·대조 로깅하는 첫 섀도우
  워크플로(CE-297). 머지/커밋/PR/Linear-write 등 실제 부작용은 0.
"""

from datetime import timedelta
from typing import Any, cast

from temporalio import workflow
from temporalio.common import RetryPolicy

# 워크플로 결정론 규칙: activity 는 sandbox 밖 모듈에서 import 해야 안전하다.
with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import evaluate_governance_activity


@workflow.defn
class HealthCheckWorkflow:
    """워커 기동·연결 검증용 최소 워크플로.

    입력 이름을 받아 확인 문자열을 반환한다. 부작용(activity 호출 등)이 없어
    Temporal 서버가 스케줄링 경로만 검증하면 되는 스모크 테스트에 쓴다.
    """

    @workflow.run
    async def run(self, name: str = "clickeye") -> str:
        return f"clickeye-temporal-ok: {name}"


@workflow.defn
class ShadowDeliveryWorkflow:
    """P1 첫 섀도우 워크플로 — 거버넌스 결정 미러링(부작용 0).

    bash 파이프라인(auto_dev_pipeline.sh)의 거버넌스 판정과 **대조**할 목적으로,
    동일한 입력(base/head/files/plan_text)을 받아 governance 커널을 실행하고
    그 결정을 로깅·반환만 한다. 머지/커밋/PR/Linear-write activity 는 두지 않는다.

    결정론 유지: 커널의 실제 실행(IO 포함)은 evaluate_governance_activity 에 위임한다.
    """

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        decision = await workflow.execute_activity(
            evaluate_governance_activity,
            payload,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        # 대조 로깅: bash 게이트 판정과 비교할 수 있도록 핵심 필드를 남긴다.
        workflow.logger.info(
            "ShadowDelivery 거버넌스 미러링: issue=%s merge_decision=%s "
            "tier=%s verdict=%s failures=%s",
            decision.get("issue_key"),
            decision.get("merge_decision"),
            decision.get("tier"),
            decision.get("verdict"),
            decision.get("failures"),
        )
        return cast("dict[str, Any]", decision)
