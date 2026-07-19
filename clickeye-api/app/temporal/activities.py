"""Temporal activity 정의 (CE-297, P1 섀도우).

Temporal 규칙상 부작용/IO(여기서는 governance 커널의 git·파일 조회)는 반드시
`@activity.defn` 안에서 수행한다. 워크플로 코드는 결정론을 지켜야 하므로 직접 IO 를
호출하지 않고 이 activity 를 통해서만 governance 결정을 얻는다.

P1 섀도우 범위: governance 결정을 **미러링**할 뿐 머지/커밋/PR/Linear-write 등 실제
부작용은 일절 수행하지 않는다. git 접근도 하지 않는다 — 변경 파일 목록(`files`)은
셸 트리거가 bash 게이트와 동일한 three-dot(`git diff --name-only main...HEAD`) 방식으로
계산해 payload 로 전달한다(대조 성립).
"""

import logging

from temporalio import activity

logger = logging.getLogger("temporal.activities")


@activity.defn
async def evaluate_governance_activity(payload: dict) -> dict:
    """governance 커널을 호출해 거버넌스 결정 dict 를 반환한다.

    payload 키:
    - base: 비교 기준 브랜치 (예: "main")
    - head: 대상 브랜치 (예: "ralph/CE-297")
    - files: 변경 파일 목록 (셸 트리거가 three-dot 으로 계산해 전달, git 미접근)
    - plan_text: (선택) plan-trace 용 텍스트, 없으면 None

    반환: governance.core.evaluate 결과 dict
      (merge_decision / tier / verdict / failures / issue_key / changed_files ...).
    """
    # editable 설치된 governance 커널(clickeye-governance). api venv/이미지에서 import 가능.
    from governance.core import evaluate

    result = evaluate(
        base=payload["base"],
        head=payload["head"],
        files=payload.get("files"),
        project_dir=None,  # 원격/컨테이너 컨텍스트: git 재해석 회피, files 인자 신뢰
        plan_text=payload.get("plan_text"),
    )
    logger.info(
        "governance 결정(activity): issue=%s merge_decision=%s tier=%s verdict=%s",
        result.get("issue_key"),
        result.get("merge_decision"),
        result.get("tier"),
        result.get("verdict"),
    )
    return result
