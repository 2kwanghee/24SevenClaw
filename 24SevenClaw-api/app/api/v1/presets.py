from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.preset import (
    NaturalLanguageConfigRequest,
    PresetApplyResponse,
    PresetListResponse,
    PresetResponse,
)
from app.services.preset_service import PresetService

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("/", response_model=PresetListResponse)
async def list_presets(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    maturity_level: str | None = Query(None),
    solution_type: str | None = Query(None),
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> PresetListResponse:
    """프리셋 목록 조회. maturity_level, solution_type 필터 지원."""
    service = PresetService(db)
    presets, total = await service.list_presets(
        offset=offset,
        limit=limit,
        maturity_level=maturity_level,
        solution_type=solution_type,
    )
    return PresetListResponse(
        items=[PresetResponse.model_validate(p) for p in presets],
        total=total,
    )


@router.get("/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: UUID,
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> PresetResponse:
    """프리셋 상세 조회."""
    service = PresetService(db)
    preset = await service.get_by_id(preset_id)
    return PresetResponse.model_validate(preset)


@router.post(
    "/{preset_id}/apply",
    response_model=PresetApplyResponse,
    status_code=status.HTTP_200_OK,
)
async def apply_preset(
    preset_id: UUID,
    data: NaturalLanguageConfigRequest | None = None,
    project_id: UUID | None = Query(None),
    user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
) -> PresetApplyResponse:
    """프리셋을 프로젝트에 적용."""
    if project_id is None:
        from app.core.exceptions import AppError

        raise AppError("PROJECT_ID_REQUIRED", "project_id 쿼리 파라미터가 필요합니다", 400)

    service = PresetService(db)
    result = await service.apply_preset(
        project_id=project_id,
        preset_id=preset_id,
        owner_id=user.id,  # type: ignore[arg-type]
    )
    return PresetApplyResponse(**result)


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
)
async def seed_presets(
    user: User = Depends(require_permission("preset:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """시스템 프리셋 시드 데이터 로드 (관리자 전용)."""
    service = PresetService(db)
    count = await service.seed_presets()
    return {"seeded": count}
