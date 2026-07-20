"""Temporal 워커 엔트리포인트 (CE-296).

`python -m app.temporal.worker` 로 실행하는 독립 프로세스다. FastAPI lifespan 에
얹지 않는다 — 워커는 blocking(`worker.run()`) 이라 API 서버 이벤트 루프를 막기 때문.

회귀 0 원칙:
- `feature_temporal` 토글이 꺼져 있으면(기본값 False) 로그만 남기고 즉시 종료한다.
  Temporal 서버가 없어도 연결 시도조차 하지 않으므로 에러가 발생하지 않는다.
- 토글이 켜져 있을 때만 Temporal 서버에 연결해 워커를 기동한다.
"""

import asyncio
import logging

from app.config import settings
from app.temporal.activities import evaluate_governance_activity
from app.temporal.workflows import HealthCheckWorkflow, ShadowDeliveryWorkflow

logger = logging.getLogger("temporal.worker")


async def run_worker() -> None:
    """워커 본체. 토글 off 면 아무 것도 하지 않는다."""
    if not settings.feature_temporal:
        # 회귀 0: 토글 꺼짐 → 서버 연결 없이 즉시 반환 (에러 없음)
        logger.info(
            "feature_temporal=off → Temporal 워커를 기동하지 않습니다 (회귀 0)."
        )
        return

    # 무거운 SDK import 는 토글 on 경로에서만 (off 실행 시 불필요한 의존성 로드 회피)
    from temporalio.client import Client
    from temporalio.worker import Worker

    logger.info(
        "Temporal 워커 기동: host=%s namespace=%s task_queue=%s",
        settings.temporal_host,
        settings.temporal_namespace,
        settings.temporal_task_queue,
    )

    client = await Client.connect(
        settings.temporal_host,
        namespace=settings.temporal_namespace,
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[HealthCheckWorkflow, ShadowDeliveryWorkflow],
        activities=[evaluate_governance_activity],
    )
    # blocking: 종료 시그널을 받을 때까지 태스크 큐를 폴링한다.
    await worker.run()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
