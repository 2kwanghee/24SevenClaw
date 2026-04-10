from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.artifact import (
    ArtifactCreate,
    ArtifactEventResponse,
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactTransitionRequest,
    ArtifactTransitionResponse,
)
from app.services.artifact_service import ArtifactService

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post(
    "/projects/{project_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_artifact(
    project_id: UUID,
    data: ArtifactCreate,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """프로젝트에 새 산출물을 생성한다 (초기 상태: draft)."""
    service = ArtifactService(db)
    artifact = await service.create(project_id=project_id, data=data)
    return ArtifactResponse.model_validate(artifact)


@router.get(
    "/projects/{project_id}/artifacts",
    response_model=ArtifactListResponse,
)
async def list_artifacts(
    project_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ArtifactListResponse:
    """프로젝트의 산출물 목록을 조회한다."""
    service = ArtifactService(db)
    artifacts, total = await service.list_by_project(
        project_id=project_id,
        offset=offset,
        limit=limit,
        status_filter=status_filter,
    )
    return ArtifactListResponse(
        items=[ArtifactResponse.model_validate(a) for a in artifacts],
        total=total,
    )


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ArtifactResponse:
    """산출물 상세 정보를 조회한다."""
    service = ArtifactService(db)
    artifact = await service.get(artifact_id)
    return ArtifactResponse.model_validate(artifact)


@router.put("/{artifact_id}/transition", response_model=ArtifactTransitionResponse)
async def transition_artifact(
    artifact_id: UUID,
    data: ArtifactTransitionRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ArtifactTransitionResponse:
    """산출물의 상태를 전이한다. 허용된 전이만 가능."""
    service = ArtifactService(db)
    artifact, event = await service.transition(artifact_id=artifact_id, data=data)
    return ArtifactTransitionResponse(
        artifact=ArtifactResponse.model_validate(artifact),
        event=ArtifactEventResponse.model_validate(event),
    )


@router.get(
    "/{artifact_id}/history",
    response_model=list[ArtifactEventResponse],
)
async def get_artifact_history(
    artifact_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> list[ArtifactEventResponse]:
    """산출물의 상태 변경 이력을 조회한다."""
    service = ArtifactService(db)
    events = await service.get_history(artifact_id)
    return [ArtifactEventResponse.model_validate(e) for e in events]
