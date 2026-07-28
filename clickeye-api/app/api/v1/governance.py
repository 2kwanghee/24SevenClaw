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
from governance.control import SUPPORTED_SCHEMA_VERSIONS
from governance.policy import PolicyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.governance import (
    ControlPlaneRejection,
    ControlPlaneSubmitRequest,
    ControlPlaneSubmitResponse,
    GovernanceEvaluateRequest,
    GovernanceEvaluateResponse,
    GovernancePolicyResponse,
)
from app.schemas.seat import SeatTokenRequest, SeatTokenResponse
from app.services.control_plane_service import ControlPlaneService
from app.services.governance_gate_service import GovernanceGateService
from app.services.intake_service import IntakeService
from app.services.project_service import ProjectService
from app.services.seat_service import SeatService

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


@router.put(
    "/control-plane",
    response_model=ControlPlaneSubmitResponse,
    responses={
        401: {"description": "서비스 키 없음/무효"},
        404: {"model": ControlPlaneRejection, "description": "프로젝트 없음"},
        422: {"model": ControlPlaneRejection, "description": "제어면 YAML 형식 불량(fail-closed)"},
    },
)
async def submit_control_plane(
    req: ControlPlaneSubmitRequest,
    x_clickeye_service_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> ControlPlaneSubmitResponse:
    """서비스 #2(기획)가 자동 생성한 제어면 YAML 을 수신한다 (다프로젝트화 P2, D-14).

    인증은 인테이크와 동일한 X-ClickEye-Service-Key 머신 헤더(신뢰 모델 v1: 인증=서비스 키
    채널, 무결성=sha256 콘텐츠 해시). 검증은 fail-closed — 불량 YAML 은 절대 기본값으로
    조용히 폴백하지 않고 422 + 기계 소비형 거부 사유(ControlPlaneRejection)로 반환한다.
    서비스 #2 는 그 body 를 자기 콜백/재생성 루프에 그대로 실을 수 있다.
    """
    # 인테이크와 동일한 서비스 키 인증 재사용(별도 인증 체계를 만들지 않는다).
    await IntakeService(db).authenticate_key(x_clickeye_service_key)

    try:
        profile, plane = await ControlPlaneService(db).submit(
            project_id=req.project_id, control_yaml=req.control_yaml
        )
    except AppError as exc:
        # 거부를 기계가 소비 가능한 형태로 — 서비스 #2 콜백 payload 계약.
        raise HTTPException(
            status_code=exc.status_code,
            detail=ControlPlaneRejection(
                code=exc.code,
                reasons=[exc.message],
                schema_supported=list(SUPPORTED_SCHEMA_VERSIONS),
            ).model_dump(),
        ) from exc

    return ControlPlaneSubmitResponse(
        project_id=req.project_id,
        schema_version=plane.schema_version,
        tier=plane.tier,
        source_signature=str(profile.source_signature),
        effective=plane.to_dict(),
    )


@router.post(
    "/seat-token",
    response_model=SeatTokenResponse,
    dependencies=[Depends(verify_governance_token)],
    responses={
        404: {"description": "프로젝트 없음 또는 사용할 시트 없음"},
        409: {"description": "시트가 active 아님(exhausted|blocked)"},
    },
)
async def issue_seat_token(
    req: SeatTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> SeatTokenResponse:
    """프로젝트 실행용 구독 시트 토큰을 머신에게 발급한다 (다프로젝트화 P4).

    파이프라인 러너가 `CLAUDE_CODE_OAUTH_TOKEN` 으로 주입할 평문 토큰을 반환하는
    유일한 경로다. 우선순위는 프로젝트 배정 시트(settings.seat_user_id) → 프로젝트
    소유자 시트이며, active 가 아닌 시트는 409 로 거부한다(조용한 우회 금지).
    인증은 다른 머신 엔드포인트와 동일한 X-Governance-Token 헤더.
    """
    project = await ProjectService(db).get_for_admin(req.project_id)
    seat, token = await SeatService(db).resolve_token_for_project(project)
    return SeatTokenResponse(seat_id=seat.id, user_id=seat.user_id, token=token)


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
