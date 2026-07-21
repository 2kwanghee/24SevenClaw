"""거버넌스 게이트 API — 머지 직전 검증/위험분류를 HTTP 로 노출(SSOT 위임).

로직은 저장소 루트 커널(governance.core)에 단일 존재하고 이 라우터는 위임만 한다.
머신-투-머신 호출용이므로 사용자 JWT 대신 머신 토큰(X-Governance-Token) 헤더로 보호한다.
settings.governance_service_token 이 비어있으면(dev) 인증 없이 개방한다.
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.governance import (
    GovernanceEvaluateRequest,
    GovernanceEvaluateResponse,
    GovernancePolicyResponse,
)
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
    # None 필드 제외 → triage off 응답에 triage/risk_score/triage_reasons/budget 키가
    # null 로 새지 않도록(커널 "off면 triage 키 미포함" 계약과 정합). on 시엔 값이 있어 포함.
    response_model_exclude_none=True,
    dependencies=[Depends(verify_governance_token)],
)
async def evaluate_governance(
    req: GovernanceEvaluateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """변경 파일/브랜치를 커널로 평가하여 머지 판정(direct/pr/block)을 반환한다.

    db 세션은 주입하되 실제 원장 조회는 트리아지 예산 opt-in + project_id 가 있을 때만
    수행된다(그 외엔 세션 미사용 → 연결도 없음). 현행 DB-less 계약과 하위호환.
    """
    return await GovernanceGateService(db).evaluate(req)


@router.get("/policy", response_model=GovernancePolicyResponse)
async def get_governance_policy(
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """전역 머지-게이트 정책 요약을 반환한다(딜리버리 콘솔 거버넌스 패널용).

    커널(governance.core.policy_summary)이 SSOT 이며 서비스는 위임만 한다. 로그인 사용자면
    누구나 조회 가능(읽기 전용, 신규 권한 없음). 토글 상태는 API 서버 env 기준(source_note).
    """
    return GovernanceGateService().get_policy()
