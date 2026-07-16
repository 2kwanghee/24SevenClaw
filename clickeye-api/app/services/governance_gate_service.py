"""거버넌스 게이트 서비스 — SSOT 커널 위임 전용.

BaseService 가 아니며 DB 를 쓰지 않는다. 검증/위험분류 로직은 저장소 루트의 stdlib 전용
커널 패키지 `governance.core` 에 단일 존재하고, 여기서는 그 evaluate() 를 그대로 호출만
한다(로직 0줄). 원격 HTTP 는 호출자의 git/.ralph 에 접근할 수 없으므로 project_dir 를
None 으로 넘겨 plan-trace 는 skip(비블로킹)되고, files+head(+plan_text)로만 평가한다.
"""

from __future__ import annotations

from typing import Any

from app.schemas.governance import GovernanceEvaluateRequest


class GovernanceGateService:
    def evaluate(self, req: GovernanceEvaluateRequest) -> dict[str, Any]:
        # 커널은 저장소 루트 패키지 → clickeye-governance 의존성(editable)으로 import 가능.
        from governance.core import evaluate as kernel_evaluate

        # 원격 HTTP 는 git 이 없을 수 있고 접근해서도 안 된다. files 미지정(None)이면
        # evaluate 가 os.getcwd() 에서 git diff 를 실행하려다 서버에서 500/블로킹되므로
        # 빈 목록으로 강제 → git 미접근 불변식 보존(계약면 변경 없음으로 평가).
        return kernel_evaluate(
            base=req.base,
            head=req.head,
            files=req.files or [],
            project_dir=None,
            plan_text=req.plan_text,
        )
