"""거버넌스 게이트 HTTP 스키마.

커널(governance.core.evaluate)의 입력/출력을 그대로 옮긴다. 로직은 없다.
응답은 마스터 off 시 축약 스키마도 허용해야 하므로 permissive(extra allow)로 둔다.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GovernanceEvaluateRequest(BaseModel):
    base: str = "main"
    head: str
    # 원격 HTTP 호출자는 git 접근이 없으므로 변경 파일을 명시적으로 넘긴다.
    files: list[str] | None = None
    # plan-trace 검사용 본문(선택). 없으면 원격에서는 skip(비블로킹).
    plan_text: str | None = None
    # ── 트리아지(항목 G, opt-in) ─────────────────────────────────────────────
    # project_id 가 있으면 서비스가 원장(LlmLedgerService)으로 usage 를 구성해 커널에
    # 주입한다(예산 축). usage 를 직접 주면 그 값이 우선(원장 조회 skip). 둘 다 없으면
    # usage=None → 예산 skip(비블로킹, 하위호환).
    project_id: UUID | None = None
    usage: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None


class GovernanceEvaluateResponse(BaseModel):
    """evaluate() 반환 dict 형식화. 축약(off)/전체(on)/트리아지 스키마를 모두 수용."""

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
    # ── 트리아지 관측 키(트리아지 opt-in 시에만 채워짐; 기본 미포함) ──────────────
    # 전부 기본 None → 엔드포인트의 response_model_exclude_none=True 로 off 시 응답에서 제외.
    # (triage_reasons 도 [] 대신 None 기본이어야 off 응답에 빈 리스트가 새지 않음.)
    triage: str | None = None
    risk_score: float | None = None
    triage_reasons: list[str] | None = None
    budget: dict[str, Any] | None = None

    model_config = {"extra": "allow"}
