from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.generate import GenerateRequest, RedownloadRequest
from app.schemas.preview import PreviewRequest, PreviewResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.schemas.wizard_config import WizardConfigResponse, WizardConfigSave, WizardData
from app.services.generate_service import generate_zip
from app.services.pm_markdown_service import serialize_pm_to_markdown
from app.services.preview_service import generate_preview
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(require_permission("project:create")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.create(owner_id=user.id, data=data)  # type: ignore[arg-type]
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
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.get_by_id(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    project = await service.update(
        project_id=project_id, owner_id=user.id, data=data  # type: ignore[arg-type]
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


@router.post("/draft/preview", response_model=PreviewResponse)
async def preview_draft(
    data: PreviewRequest,
    user: User = Depends(get_current_user),
) -> PreviewResponse:
    """프로젝트 생성 전 위저드 프리뷰 (인증만 필요, 프로젝트 ID 불필요)."""
    return generate_preview(data)


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

    return generate_preview(data)


async def _resolve_pm(
    db: AsyncSession,
    pm_slug: str | None,
    pm_profile_id: UUID | None = None,
) -> tuple[str | None, str | None, list[dict[str, Any]] | None]:
    """pm_profile_id(우선) 또는 pm_slug로 PM 프로필과 compositions을 조회한다.

    Returns:
        (slug, markdown, compositions) — 프로필 없으면 (None, None, None)
    """
    if not pm_slug and not pm_profile_id:
        return None, None, None

    from sqlalchemy import select

    from app.models.pm_composition import PMComposition
    from app.models.pm_profile import PMProfile

    if pm_profile_id:
        result = await db.execute(
            select(PMProfile).where(PMProfile.id == pm_profile_id)
        )
    else:
        result = await db.execute(
            select(PMProfile).where(PMProfile.slug == pm_slug)
        )

    profile = result.scalar_one_or_none()
    if profile is None:
        return None, None, None

    # Compositions 로드 (display_order 순)
    comp_result = await db.execute(
        select(PMComposition)
        .where(PMComposition.pm_id == profile.id)
        .order_by(PMComposition.display_order)
    )
    compositions: list[dict[str, Any]] = [
        {
            "component_type": c.component_type,
            "component_slug": c.component_slug,
            "is_required": c.is_required,
        }
        for c in comp_result.scalars().all()
    ]

    return str(profile.slug), serialize_pm_to_markdown(profile), compositions or None


@router.post("/draft/generate")
async def generate_draft(
    data: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """프로젝트 생성 전 드래프트 ZIP 다운로드 (project ID 불필요)."""
    project_name = data.solution.get("projectName", "project")
    pm_slug, pm_markdown, pm_compositions = await _resolve_pm(
        db, pm_slug=data.pm_slug, pm_profile_id=data.pm_profile_id
    )
    buffer = generate_zip(
        data, project_name,
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
    )

    filename = f"{project_name}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/{project_id}/generate")
async def generate_project(
    project_id: UUID,
    data: GenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """위저드 설정 + API 키 기반 ZIP 파일 스트리밍 다운로드."""
    from datetime import UTC, datetime

    service = ProjectService(db)
    project = await service.get_by_id(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]

    project_name = data.solution.get("projectName", project.name)
    pm_slug, pm_markdown, pm_compositions = await _resolve_pm(
        db, pm_slug=data.pm_slug, pm_profile_id=data.pm_profile_id
    )
    buffer = generate_zip(
        data, project_name,
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
    )

    # 위저드 설정 자동 저장 (env_vars 제외)
    wizard_data = WizardConfigSave(
        wizard_data=WizardData(
            organization=data.organization,
            solution=data.solution,
            agents=[{"id": a} for a in data.agents],
            skills=[{"id": s} for s in data.skills],
            pipelines=[{"id": p} for p in data.pipelines],
            platform=data.platform,
        )
    )
    await service.save_wizard_config(
        project_id=project_id, owner_id=user.id, data=wizard_data  # type: ignore[arg-type]
    )

    # pm_profile_id 영속화
    if data.pm_profile_id is not None:
        project.pm_profile_id = data.pm_profile_id  # type: ignore[assignment]
        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await db.commit()

    filename = f"{project_name}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/{project_id}/redownload")
async def redownload_project(
    project_id: UUID,
    data: RedownloadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """저장된 위저드 설정으로 ZIP 재생성. env_vars만 새로 전달."""
    from app.core.exceptions import AppError

    service = ProjectService(db)
    project = await service.get_wizard_config(
        project_id=project_id, owner_id=user.id  # type: ignore[arg-type]
    )

    if not project.wizard_data:
        raise AppError(
            "CONFIG_NOT_FOUND", "저장된 위저드 설정이 없습니다", 400
        )

    wd = project.wizard_data
    gen_request = GenerateRequest(
        organization=wd.get("organization", {}),
        solution=wd.get("solution", {}),
        agents=[a["id"] for a in wd.get("agents", []) if "id" in a],
        skills=[s["id"] for s in wd.get("skills", []) if "id" in s],
        pipelines=[p["id"] for p in wd.get("pipelines", []) if "id" in p],
        platform=wd.get("platform", {}),
        env_vars=data.env_vars,
    )

    project_name = gen_request.solution.get("projectName", project.name)

    # 저장된 pm_profile_id로 PM 데이터 복원
    stored_pm_id: UUID | None = project.pm_profile_id  # type: ignore[assignment]
    pm_slug, pm_markdown, pm_compositions = await _resolve_pm(
        db, pm_slug=None, pm_profile_id=stored_pm_id
    )

    buffer = generate_zip(
        gen_request, project_name,
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
    )

    filename = f"{project_name}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/{project_id}/config", response_model=WizardConfigResponse)
async def save_wizard_config(
    project_id: UUID,
    data: WizardConfigSave,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WizardConfigResponse:
    service = ProjectService(db)
    project = await service.save_wizard_config(
        project_id=project_id, owner_id=user.id, data=data  # type: ignore[arg-type]
    )
    return WizardConfigResponse(
        project_id=project.id,
        wizard_data=project.wizard_data,
        updated_at=project.updated_at,
    )


@router.get("/{project_id}/config", response_model=WizardConfigResponse)
async def get_wizard_config(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WizardConfigResponse:
    service = ProjectService(db)
    project = await service.get_wizard_config(
        project_id=project_id, owner_id=user.id  # type: ignore[arg-type]
    )
    return WizardConfigResponse(
        project_id=project.id,
        wizard_data=project.wizard_data,
        updated_at=project.updated_at,
    )
