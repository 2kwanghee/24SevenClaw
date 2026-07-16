"""거버넌스 게이트 HTTP 스키마.

커널(governance.core.evaluate)의 입력/출력을 그대로 옮긴다. 로직은 없다.
응답은 마스터 off 시 축약 스키마도 허용해야 하므로 permissive(extra allow)로 둔다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GovernanceEvaluateRequest(BaseModel):
    base: str = "main"
    head: str
    # 원격 HTTP 호출자는 git 접근이 없으므로 변경 파일을 명시적으로 넘긴다.
    files: list[str] | None = None
    # plan-trace 검사용 본문(선택). 없으면 원격에서는 skip(비블로킹).
    plan_text: str | None = None


class GovernanceEvaluateResponse(BaseModel):
    """evaluate() 반환 dict 형식화. 축약(off)/전체(on) 스키마를 모두 수용."""

    governance: str
    verdict: str
    tier: str
    merge_decision: str
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issue_key: str | None = None
    checks: dict[str, Any] = Field(default_factory=dict)
    risk_reasons: list[str] = Field(default_factory=list)
    changed_files: int | None = None

    model_config = {"extra": "allow"}
