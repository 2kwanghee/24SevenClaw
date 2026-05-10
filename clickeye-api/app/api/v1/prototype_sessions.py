"""프로토타입 세션 API 라우터 — 8개 엔드포인트."""

import contextlib
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.prototype import (
    FinalizeRequest,
    FinalizeResponse,
    GenerateStartResponse,
    PMRecommendItemResponse,
    PrototypeListResponse,
    PrototypeResponse,
    PrototypeSessionCreate,
    PrototypeSessionResponse,
    PrototypeSessionStatusResponse,
    PrototypeSessionUpdate,
    RecommendComponentsResponse,
    RecommendPMsResponse,
)
from app.services.prototype_service import PrototypeService

# 테스트에서 이 변수를 TestSession으로 교체할 수 있다.
_bg_session_factory: Any = async_session


async def _run_generation_bg(session_id: UUID, user_id: UUID) -> None:
    """독립 DB 세션으로 백그라운드 프로토타입 생성을 실행한다."""
    import traceback  # noqa: PLC0415
    try:
        async with _bg_session_factory() as db:
            service = PrototypeService(db)
            with contextlib.suppress(Exception):
                await service.run_generation(session_id=session_id, user_id=user_id)
    except Exception:
        print(f"[BG_ERROR] session={session_id}\n{traceback.format_exc()}", flush=True)

router = APIRouter(prefix="/prototype-sessions", tags=["prototype-sessions"])


@router.post(
    "/",
    response_model=PrototypeSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    data: PrototypeSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeSessionResponse:
    """프로토타입 세션을 생성한다."""
    service = PrototypeService(db)
    session = await service.create_session(user_id=user.id, data=data)  # type: ignore[arg-type]
    return PrototypeSessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=PrototypeSessionResponse)
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeSessionResponse:
    """프로토타입 세션을 조회한다."""
    service = PrototypeService(db)
    session = await service.get_session(session_id=session_id, user_id=user.id)  # type: ignore[arg-type]
    return PrototypeSessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=PrototypeSessionResponse)
async def update_session(
    session_id: UUID,
    data: PrototypeSessionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeSessionResponse:
    """세션의 선택 정보(프로토타입/PM/스텝)를 업데이트한다."""
    service = PrototypeService(db)
    session = await service.update_session(
        session_id=session_id, user_id=user.id, data=data  # type: ignore[arg-type]
    )
    return PrototypeSessionResponse.model_validate(session)


@router.get(
    "/{session_id}/status", response_model=PrototypeSessionStatusResponse
)
async def get_session_status(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeSessionStatusResponse:
    """프로토타입 세션 상태를 조회한다."""
    service = PrototypeService(db)
    session = await service.get_session_status(
        session_id=session_id, user_id=user.id  # type: ignore[arg-type]
    )
    return PrototypeSessionStatusResponse.model_validate(session)


@router.get(
    "/{session_id}/prototypes", response_model=PrototypeListResponse
)
async def list_prototypes(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeListResponse:
    """세션의 프로토타입 목록을 반환한다."""
    service = PrototypeService(db)
    prototypes = await service.list_prototypes(
        session_id=session_id, user_id=user.id  # type: ignore[arg-type]
    )
    return PrototypeListResponse(
        items=[PrototypeResponse.model_validate(p) for p in prototypes],
        total=len(prototypes),
    )


@router.post(
    "/{session_id}/prototypes/generate",
    response_model=GenerateStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_prototypes(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateStartResponse:
    """프로토타입 생성을 시작한다 (비동기 백그라운드 처리).

    즉시 202 Accepted를 반환하고 백그라운드에서 생성을 진행한다.
    클라이언트는 GET /{session_id}/status 를 폴링하여 완료 여부를 확인한다.
    """
    live_preview_enabled = False
    if user.organization_id:  # type: ignore[truthy-bool]
        org = await db.get(Organization, user.organization_id)
        if org:
            live_preview_enabled = bool((org.features or {}).get("live_preview_enabled", False))
    if not live_preview_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="라이브 프리뷰 기능이 현재 비활성화되어 있습니다. 관리자에게 문의하세요.",
        )

    service = PrototypeService(db)
    await service.start_generation(
        session_id=session_id, user_id=user.id  # type: ignore[arg-type]
    )
    background_tasks.add_task(
        _run_generation_bg, session_id, user.id  # type: ignore[arg-type]
    )
    return GenerateStartResponse(
        task_id=session_id,
        session_id=session_id,
        status="generating",
        message="프로토타입 생성이 시작되었습니다",
    )


@router.get(
    "/{session_id}/recommend-components",
    response_model=RecommendComponentsResponse,
)
async def recommend_components(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendComponentsResponse:
    """선택된 프로토타입 기반으로 에이전트·스킬·카탈로그 slug를 추천한다.

    선택된 프로토타입이 없으면 409를 반환한다.
    위저드의 '에이전트 선택' 스텝에서 자동 pre-select에 사용한다.
    """
    service = PrototypeService(db)
    result = await service.recommend_components_for_session(
        session_id=session_id, user_id=user.id  # type: ignore[arg-type]
    )
    return RecommendComponentsResponse(**result)


@router.post(
    "/{session_id}/recommend-pms",
    response_model=RecommendPMsResponse,
)
async def recommend_pms(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendPMsResponse:
    """세션의 선택된 프로토타입 기반으로 PM을 추천한다.

    선택된 프로토타입이 없으면 409를 반환한다.
    """
    service = PrototypeService(db)
    recommendations = await service.recommend_pms_for_session(
        session_id=session_id, user_id=user.id  # type: ignore[arg-type]
    )

    items = []
    for rec in recommendations:
        profile = rec["pm_profile"]
        items.append(
            PMRecommendItemResponse(
                pm_id=profile.id,
                name=str(profile.name),
                slug=str(profile.slug),
                avatar_url=profile.avatar_url,
                title=profile.title,
                domain=profile.domain,
                match_score=int(rec["match_score"]),
                reasoning=str(rec["reasoning"]),
            )
        )

    return RecommendPMsResponse(items=items)


@router.post(
    "/{session_id}/finalize",
    response_model=FinalizeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def finalize_session(
    session_id: UUID,
    data: FinalizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinalizeResponse:
    """세션을 확정하고 최종 프로젝트를 생성한다.

    선택된 프로토타입과 PM이 없으면 409를 반환한다.
    """
    service = PrototypeService(db)
    project = await service.finalize_session(
        session_id=session_id,
        user_id=user.id,  # type: ignore[arg-type]
        data=data,
        organization_id=user.organization_id,  # type: ignore[arg-type]
    )
    return FinalizeResponse(
        project_id=project.id,
        project_name=str(project.name),
        session_id=session_id,
        message="프로젝트가 생성되었습니다",
        initial_task_url=project.initial_task_url,
    )


# ── 목록 및 삭제 (보조 엔드포인트) ──

@router.get("/", response_model=list[PrototypeSessionResponse])
async def list_sessions(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PrototypeSessionResponse]:
    """사용자의 프로토타입 세션 목록을 반환한다."""
    service = PrototypeService(db)
    sessions, _total = await service.list_sessions(
        user_id=user.id, offset=offset, limit=limit  # type: ignore[arg-type]
    )
    return [PrototypeSessionResponse.model_validate(s) for s in sessions]


@router.delete(
    "/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """프로토타입 세션을 삭제한다."""
    service = PrototypeService(db)
    await service.delete_session(session_id=session_id, user_id=user.id)  # type: ignore[arg-type]
