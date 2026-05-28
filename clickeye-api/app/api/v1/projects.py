from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
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
    ProjectResetResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.schemas.wizard_config import WizardConfigResponse, WizardConfigSave, WizardData
from app.services import setup_token_service
from app.services.env_resolver import merge_saved_credentials_into_env
from app.services.generate_service import generate_zip
from app.services.pm_markdown_service import serialize_pm_to_markdown
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


async def _resolve_catalog_entry(
    db: AsyncSession, slug: str | None
) -> dict[str, Any] | None:
    """slug로 카탈로그 엔트리를 조회하여 dict로 반환. 없으면 None."""
    if not slug:
        return None
    from app.services.prototype_catalog_service import PrototypeCatalogService

    svc = PrototypeCatalogService(db)
    try:
        entry = await svc.get_entry_by_slug(slug)
    except Exception:
        return None
    return {col.key: getattr(entry, col.key) for col in entry.__table__.columns}


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
    auth_method: str = getattr(data, "auth_method", None) or "api_key"

    # 등록된 API 키로 빈 항목 자동 채움 (입력값 우선, OAuth 모드는 Anthropic 키 채움 스킵)
    data.env_vars = await merge_saved_credentials_into_env(
        user_id=user.id,  # type: ignore[arg-type]
        project_id=None,
        db=db,
        env_vars=dict(data.env_vars or {}),
        auth_method=auth_method,
    )

    pm_slug, pm_markdown, pm_compositions = await _resolve_pm(
        db, pm_slug=data.pm_slug, pm_profile_id=data.pm_profile_id
    )
    catalog_entry = await _resolve_catalog_entry(
        db, data.catalog_entry_slug or data.solution.get("catalogEntrySlug")
    )
    buffer = await generate_zip(
        data, project_name,
        db=db,
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
        catalog_entry=catalog_entry,
        locale=getattr(data, "locale", "ko") or "ko",
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
    service = ProjectService(db)
    project = await service.get_by_id(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]

    project_name = data.solution.get("projectName", project.name)
    pm_slug, pm_markdown, pm_compositions = await _resolve_pm(
        db, pm_slug=data.pm_slug, pm_profile_id=data.pm_profile_id
    )
    catalog_entry = await _resolve_catalog_entry(
        db, data.catalog_entry_slug or data.solution.get("catalogEntrySlug")
    )

    auth_method: str = getattr(data, "auth_method", None) or "api_key"

    # 등록된 API 키로 빈 항목 자동 채움 (입력값 우선, OAuth 모드는 Anthropic 키 채움 스킵)
    data.env_vars = await merge_saved_credentials_into_env(
        user_id=user.id,  # type: ignore[arg-type]
        project_id=project_id,
        db=db,
        env_vars=dict(data.env_vars or {}),
        auth_method=auth_method,
    )

    setup_token = await setup_token_service.issue_for_project(db, project_id, user.id)  # type: ignore[arg-type]
    buffer = await generate_zip(
        data, project_name,
        db=db,
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
        catalog_entry=catalog_entry,
        setup_token=setup_token,
        clickeye_project_id=str(project_id),
        locale=getattr(data, "locale", "ko") or "ko",
    )

    # catalogEntrySlug 와 authMethod 를 solution에 병합하여 재다운로드 시 복원 가능하게 저장
    persisted_solution = {**data.solution}
    if data.catalog_entry_slug:
        persisted_solution["catalogEntrySlug"] = data.catalog_entry_slug
    persisted_solution["authMethod"] = auth_method

    # 위저드 설정 자동 저장 (env_vars 제외)
    wizard_data = WizardConfigSave(
        wizard_data=WizardData(
            organization=data.organization,
            solution=persisted_solution,
            agents=[{"id": a} for a in data.agents],
            skills=[{"id": s} for s in data.skills],
            pipelines=[{"id": p} for p in data.pipelines],
            platform=data.platform,
        )
    )
    await service.save_wizard_config(
        project_id=project_id, owner_id=user.id, data=wizard_data  # type: ignore[arg-type]
    )

    # pm_profile_id 영속화 + 다운로드 timestamp 갱신
    now = datetime.now(UTC)
    if data.pm_profile_id is not None:
        project.pm_profile_id = data.pm_profile_id  # type: ignore[assignment]
    project.last_zip_downloaded_at = now  # type: ignore[assignment]
    project.updated_at = now  # type: ignore[assignment]
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

    # 저장된 인증 방식 복원 (기존 프로젝트 호환: 기본값 api_key)
    # wizard_data.solution.authMethod (generate_project 저장 경로) 또는
    # wizard_data.env.authMethod (프론트 위저드 스토어 직접 저장 경로) 중 하나
    redownload_auth_method: str = (
        wd.get("solution", {}).get("authMethod")
        or wd.get("env", {}).get("authMethod")
        or "api_key"
    )

    # 등록된 API 키로 빈 항목 자동 채움 (입력값 우선, OAuth 모드는 Anthropic 키 채움 스킵)
    merged_env = await merge_saved_credentials_into_env(
        user_id=user.id,  # type: ignore[arg-type]
        project_id=project_id,
        db=db,
        env_vars=dict(data.env_vars or {}),
        auth_method=redownload_auth_method,
    )

    gen_request = GenerateRequest(
        organization=wd.get("organization", {}),
        solution=wd.get("solution", {}),
        agents=[a["id"] for a in wd.get("agents", []) if "id" in a],
        skills=[s["id"] for s in wd.get("skills", []) if "id" in s],
        pipelines=[p["id"] for p in wd.get("pipelines", []) if "id" in p],
        hook_ids=[h["id"] for h in wd.get("hooks", []) if "id" in h],
        platform=wd.get("platform", {}),
        env_vars=merged_env,
        auth_method=redownload_auth_method,
    )

    project_name = gen_request.solution.get("projectName", project.name)

    # 저장된 pm_profile_id로 PM 데이터 복원
    stored_pm_id: UUID | None = project.pm_profile_id  # type: ignore[assignment]
    pm_slug, pm_markdown, pm_compositions = await _resolve_pm(
        db, pm_slug=None, pm_profile_id=stored_pm_id
    )

    # solution에 저장된 catalogEntrySlug로 카탈로그 엔트리 복원
    catalog_slug = wd.get("solution", {}).get("catalogEntrySlug")
    catalog_entry = await _resolve_catalog_entry(db, catalog_slug)

    redownload_setup_token = await setup_token_service.issue_for_project(db, project_id, user.id)  # type: ignore[arg-type]
    redownload_locale: str = wd.get("solution", {}).get("locale", "ko") or "ko"
    buffer = await generate_zip(
        gen_request, project_name,
        db=db,
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
        catalog_entry=catalog_entry,
        setup_token=redownload_setup_token,
        clickeye_project_id=str(project_id),
        locale=redownload_locale,
    )

    # 다운로드 timestamp 갱신
    project.last_zip_downloaded_at = datetime.now(UTC)  # type: ignore[assignment]
    project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    await db.commit()

    filename = f"{project_name}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/{project_id}/env")
async def download_project_env(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """최신 자격증명이 적용된 .env 파일만 단독 다운로드 (ZIP 재다운로드 불필요)."""
    from app.core.exceptions import AppError
    from app.engine.env_generator import generate_env_files

    service = ProjectService(db)
    project = await service.get_wizard_config(
        project_id=project_id, owner_id=user.id  # type: ignore[arg-type]
    )

    if not project.wizard_data:
        raise AppError("CONFIG_NOT_FOUND", "저장된 위저드 설정이 없습니다", 400)

    wd = project.wizard_data
    skill_ids = [s["id"] for s in wd.get("skills", []) if "id" in s]
    pipeline_ids = [p["id"] for p in wd.get("pipelines", []) if "id" in p]
    workflow_ids = skill_ids + pipeline_ids

    # 저장된 인증 방식 복원 (기존 프로젝트 호환: 기본값 api_key)
    env_auth_method: str = (
        wd.get("solution", {}).get("authMethod")
        or wd.get("env", {}).get("authMethod")
        or "api_key"
    )

    # 카탈로그 정의에서 env_var 수집
    from app.engine.catalog import get_env_var_definitions
    env_var_definitions = get_env_var_definitions(workflow_ids)

    # 등록된 API 키로 빈 항목 자동 채움 (OAuth 모드는 Anthropic 키 채움 스킵)
    stored_env: dict[str, str] = {}
    merged_env = await merge_saved_credentials_into_env(
        user_id=user.id,  # type: ignore[arg-type]
        project_id=project_id,
        db=db,
        env_vars=stored_env,
        auth_method=env_auth_method,
    )

    env_files = generate_env_files(
        env_var_definitions=env_var_definitions,
        env_vars=merged_env,
    )
    env_content = env_files.get(".env", "# 환경 변수\n")

    # 다운로드 timestamp 갱신
    project.last_env_downloaded_at = datetime.now(UTC)  # type: ignore[assignment]
    project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    await db.commit()

    return Response(
        content=env_content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=.env",
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
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
