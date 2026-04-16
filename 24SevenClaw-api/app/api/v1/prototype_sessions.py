"""프로토타입 세션 API 라우터 — 8개 엔드포인트."""

import contextlib
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.prototype import (
    GenerateStartResponse,
    PrototypeListResponse,
    PrototypeResponse,
    PrototypeSelectRequest,
    PrototypeSessionCreate,
    PrototypeSessionResponse,
    PrototypeSessionStatusResponse,
)
from app.services.prototype_service import PrototypeService

# 테스트에서 이 변수를 TestSession으로 교체할 수 있다.
_bg_session_factory: Any = async_session


async def _run_generation_bg(session_id: UUID, user_id: UUID) -> None:
    """독립 DB 세션으로 백그라운드 프로토타입 생성을 실행한다."""
    async with _bg_session_factory() as db:
        service = PrototypeService(db)
        with contextlib.suppress(Exception):
            await service.run_generation(session_id=session_id, user_id=user_id)

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


@router.post(
    "/{session_id}/generate",
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
    service = PrototypeService(db)
    await service.start_generation(
        session_id=session_id, user_id=user.id  # type: ignore[arg-type]
    )
    background_tasks.add_task(
        _run_generation_bg, session_id, user.id  # type: ignore[arg-type]
    )
    return GenerateStartResponse(
        message="프로토타입 생성이 시작되었습니다",
        session_id=session_id,
    )


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
    "/{session_id}/select", response_model=PrototypeResponse
)
async def select_prototype(
    session_id: UUID,
    data: PrototypeSelectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeResponse:
    """프로토타입을 선택한다."""
    service = PrototypeService(db)
    prototype = await service.select_prototype(
        session_id=session_id, user_id=user.id, data=data  # type: ignore[arg-type]
    )
    return PrototypeResponse.model_validate(prototype)


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
