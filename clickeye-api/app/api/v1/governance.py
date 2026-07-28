"""거버넌스 게이트 API — 머지 직전 검증/위험분류를 HTTP 로 노출(SSOT 위임).

로직은 저장소 루트 커널(governance.core)에 단일 존재하고 이 라우터는 위임만 한다.
머신-투-머신 호출용이므로 사용자 JWT 대신 머신 토큰(X-Governance-Token) 헤더로 보호한다.
settings.governance_service_token 이 비어있으면(dev) 인증 없이 개방한다.
"""

from __future__ import annotations

import secrets
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from governance.policy import PolicyError
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


def _policy_error_422(exc: PolicyError) -> HTTPException:
    """불량 프로젝트 정책 → 422. 절대 기본 정책으로 조용히 폴백하지 않는다(fail-closed).

    사유를 그대로 담아 운영자가 DeliveryProfile.policy 의 어느 키가 잘못됐는지 알 수 있게 한다.
    """
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"프로젝트 거버넌스 정책(DeliveryProfile.policy)이 유효하지 않습니다: {exc}",
    )


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

    project_id 를 주면 해당 프로젝트의 DeliveryProfile 정책으로 판정하고(미등록이면 기본
    정책 폴백 + policy_source 노출), 미지정이면 기존과 동일하게 기본 정책으로 판정한다.

    db 세션은 주입하되 실제 조회(프로파일/원장)는 project_id 가 있을 때만 수행된다
    (그 외엔 세션 미사용 → 연결도 없음). 현행 DB-less 계약과 하위호환.
    """
    try:
        return await GovernanceGateService(db).evaluate(req)
    except PolicyError as exc:
        raise _policy_error_422(exc) from exc


@router.get(
    "/policy",
    response_model=GovernancePolicyResponse,
    # project_id 미지정 시 policy_source(None)가 응답에 새지 않도록 → 기존 응답 키셋 불변.
    response_model_exclude_none=True,
)
async def get_governance_policy(
    project_id: UUID | None = Query(
        default=None,
        description="지정 시 해당 프로젝트의 DeliveryProfile 정책 기준 요약(미지정: 전역 env 기준)",
    ),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """머지-게이트 정책 요약을 반환한다(딜리버리 콘솔 거버넌스 패널용).

    커널(governance.core.policy_summary)이 SSOT 이며 서비스는 위임만 한다. 로그인 사용자면
    누구나 조회 가능(읽기 전용, 신규 권한 없음). project_id 미지정이면 전역 요약이고 토글
    상태는 API 서버 env 기준(source_note). 지정하면 프로젝트 정책 기준이며 env 를 보지 않는다.
    """
    try:
        return await GovernanceGateService(db).get_policy(project_id=project_id)
    except PolicyError as exc:
        raise _policy_error_422(exc) from exc
