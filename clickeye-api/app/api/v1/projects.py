from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.preview import PreviewRequest, PreviewResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResetResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.preview_service import generate_preview
from app.services.project_service import ProjectService, annotate_key_status

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(require_permission("project:create")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.create(
        owner_id=user.id,  # type: ignore[arg-type]
        data=data,
        organization_id=user.organization_id,  # type: ignore[arg-type]
    )
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    service = ProjectService(db)
    projects, total = await service.list_by_owner(
        owner_id=user.id,  # type: ignore[arg-type]
        offset=offset,
        limit=limit,
        search=search,
        status_filter=status_filter,
    )
    anthropic_ts, linear_ts = await service.get_user_creds_timestamps(user.id)  # type: ignore[arg-type]
    items = []
    for p in projects:
        resp = ProjectResponse.model_validate(p)
        annotate_key_status(resp, p, anthropic_ts, linear_ts)
        items.append(resp)
    return ProjectListResponse(items=items, total=total)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.get_by_id(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]
    anthropic_ts, linear_ts = await service.get_user_creds_timestamps(user.id)  # type: ignore[arg-type]
    resp = ProjectResponse.model_validate(project)
    return annotate_key_status(resp, project, anthropic_ts, linear_ts)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.update(
        project_id=project_id,
        owner_id=user.id,
        data=data,  # type: ignore[arg-type]
    )
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    user: User = Depends(require_permission("project:delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProjectService(db)
    await service.delete(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]


@router.post("/{project_id}/reset", response_model=ProjectResetResponse)
async def reset_project(
    project_id: UUID,
    user: User = Depends(require_permission("project:delete")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResetResponse:
    """프로젝트를 초기 상태로 초기화한다.
    위자드/부트스트랩/티켓/산출물/오케스트레이터 세션 등 진행 데이터를 삭제하고
    프로젝트 식별자(id, name, slug, owner)는 보존한다.
    라이선스가 있으면 새 키로 재발급된다.
    """
    service = ProjectService(db)
    return await service.reset(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]


@router.post("/draft/preview", response_model=PreviewResponse)
async def preview_draft(
    data: PreviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    """프로젝트 생성 전 위저드 프리뷰 (인증만 필요, 프로젝트 ID 불필요)."""
    return await generate_preview(data, db=db)


@router.post("/{project_id}/preview", response_model=PreviewResponse)
async def preview_project(
    project_id: UUID,
    data: PreviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    """위저드 설정 기반 파일 트리 + 내용 프리뷰 생성."""
    service = ProjectService(db)
    await service.get_by_id(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]

    return await generate_preview(data, db=db)
