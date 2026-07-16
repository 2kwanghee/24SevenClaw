"""거버넌스 게이트 API — 머지 직전 검증/위험분류를 HTTP 로 노출(SSOT 위임).

로직은 저장소 루트 커널(governance.core)에 단일 존재하고 이 라우터는 위임만 한다.
머신-투-머신 호출용이므로 사용자 JWT 대신 머신 토큰(X-Governance-Token) 헤더로 보호한다.
settings.governance_service_token 이 비어있으면(dev) 인증 없이 개방한다.
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import settings
from app.schemas.governance import GovernanceEvaluateRequest, GovernanceEvaluateResponse
from app.services.governance_gate_service import GovernanceGateService

router = APIRouter(prefix="/governance", tags=["governance"])


def verify_governance_token(
    x_governance_token: str | None = Header(default=None),
) -> None:
    """머신 토큰 검증. 토큰 미설정(dev) → 개방. 설정 시 헤더 일치 필수."""
    expected = settings.governance_service_token
    if not expected:  # None 또는 빈 문자열 → dev 개방
        return
    if x_governance_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Governance-Token 헤더가 필요합니다.",
        )
    # 타이밍 공격 방지를 위해 상수 시간 비교.
    if not secrets.compare_digest(x_governance_token, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="거버넌스 서비스 토큰이 일치하지 않습니다.",
        )


@router.post(
    "/evaluate",
    response_model=GovernanceEvaluateResponse,
    dependencies=[Depends(verify_governance_token)],
)
async def evaluate_governance(
    req: GovernanceEvaluateRequest,
) -> dict[str, Any]:
    """변경 파일/브랜치를 커널로 평가하여 머지 판정(direct/pr/block)을 반환한다."""
    return GovernanceGateService().evaluate(req)
