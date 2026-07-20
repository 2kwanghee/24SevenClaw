#!/usr/bin/env python3
"""Temporal 섀도우 트리거 (CE-297, P1).

auto_dev_pipeline.sh 가 이슈/브랜치 확정 직후 호출하는 fire-and-forget 트리거.
셸(레포 루트)은 git·Linear 에 접근 가능하므로 여기서 변경 파일 목록을 계산해
ShadowDeliveryWorkflow 인자로 전달한다. 워크플로는 governance 결정을 미러링·로깅만
하며 부작용은 0.

회귀 0 원칙:
- FLOWOPS_TEMPORAL 이 off(false/0/off/no)면 즉시 no-op(exit 0). 미설정=활성 규약이지만
  파이프라인은 셸 쪽에서 명시적으로 활성 시에만 호출하므로 여기서도 방어적으로 게이트한다.
- temporalio 미설치·Temporal 서버 미가용·연결 실패 등 어떤 예외도 WARN 로그 후 exit 0.
  섀도우는 기존 파이프라인을 절대 막지 않는다.

files 대조 방식: bash 게이트(auto_dev_pipeline.sh)의 HTTP 경로와 **동일한**
three-dot `git diff --name-only main...<head>`(merge-base) 를 사용해 커널 판정을 일치시킨다.
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys

logger = logging.getLogger("temporal.shadow_trigger")


def _is_enabled(key: str) -> bool:
    """pipeline_config.sh is_enabled 규약과 동일: 미설정=활성, false/0/off/no=비활성."""
    value = os.environ.get(key)
    if value is None or value == "":
        return True
    return value.strip().lower() not in ("false", "0", "off", "no")


def _compute_files(base: str, head: str) -> list[str]:
    """bash 게이트와 동일한 three-dot(merge-base) diff 로 변경 파일 목록 계산."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", f"{base}...{head}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # git 실패 시 빈 목록(섀도우이므로 치명적 아님)
        logger.warning("git diff 실패(무시): %s", exc)
        return []
    return [f for f in out.splitlines() if f.strip()]


async def _trigger(issue_key: str, base: str, head: str) -> None:
    # 무거운 SDK import 는 활성 경로에서만. 미설치면 graceful skip.
    from temporalio.client import Client

    host = os.environ.get("TEMPORAL_HOST", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    task_queue = os.environ.get("TEMPORAL_TASK_QUEUE", "clickeye-default")

    files = _compute_files(base, head)
    payload = {
        "base": base,
        "head": head,
        "files": files,
        "issue_key": issue_key,
        "plan_text": None,
    }

    client = await Client.connect(host, namespace=namespace)
    # fire-and-forget: 워크플로 시작만 하고 결과는 대기하지 않는다.
    # id=issue_key 로 멱등성 확보(동일 이슈 재트리거 시 중복 실행 방지).
    handle = await client.start_workflow(
        "ShadowDeliveryWorkflow",
        payload,
        id=issue_key,
        task_queue=task_queue,
    )
    logger.info(
        "ShadowDeliveryWorkflow 트리거 완료: id=%s run_id=%s files=%d host=%s",
        handle.id,
        handle.result_run_id,
        len(files),
        host,
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Temporal 섀도우 워크플로 트리거")
    parser.add_argument("--issue-key", required=True, help="Linear 이슈 키 (workflow id)")
    parser.add_argument("--base", default="main", help="비교 기준 브랜치 (기본 main)")
    parser.add_argument("--head", required=True, help="대상 브랜치")
    args = parser.parse_args()

    if not _is_enabled("FLOWOPS_TEMPORAL"):
        logger.info("FLOWOPS_TEMPORAL=off → 섀도우 트리거 no-op (회귀 0).")
        return 0

    try:
        asyncio.run(_trigger(args.issue_key, args.base, args.head))
    except ModuleNotFoundError as exc:
        logger.warning("temporalio 미설치 → 섀도우 트리거 skip: %s", exc)
        return 0
    except Exception as exc:  # 연결 실패/서버 미가용 등 — 파이프라인 안 막음
        logger.warning("Temporal 섀도우 트리거 실패(무시): %s", exc)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
