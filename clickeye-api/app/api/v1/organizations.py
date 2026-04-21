from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationResponse
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_organization(
    data: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """회사 정보를 등록하거나 수정한다."""
    service = OrganizationService(db)
    org = await service.upsert(user_id=user.id, data=data)  # type: ignore[arg-type]
    return OrganizationResponse.model_validate(org)


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """현재 사용자의 회사 정보를 조회한다."""
    service = OrganizationService(db)
    org = await service.get_by_user(user_id=user.id)  # type: ignore[arg-type]
    return OrganizationResponse.model_validate(org)
