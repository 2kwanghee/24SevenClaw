from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.preset import (
    MaturityAssessmentDetailResponse,
    MaturityAssessmentRequest,
    MaturityAssessmentResponse,
    MaturityQuestion,
)
from app.services.maturity_service import MaturityService

router = APIRouter(prefix="/maturity", tags=["maturity"])


@router.get("/questions", response_model=list[MaturityQuestion])
async def get_maturity_questions(
    db: AsyncSession = Depends(get_db),
) -> list[MaturityQuestion]:
    """성숙도 평가 질문지 조회 (인증 불요)."""
    service = MaturityService(db)
    return service.get_questions()


@router.post(
    "/assess",
    response_model=MaturityAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assess_maturity(
    data: MaturityAssessmentRequest,
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> MaturityAssessmentResponse:
    """성숙도 평가 수행 -> 점수 + 추천 프리셋 반환."""
    service = MaturityService(db)
    result = await service.assess(
        user_id=user.id,  # type: ignore[arg-type]
        answers=data.answers,
        organization_id=data.organization_id,
    )
    return MaturityAssessmentResponse(**result)


@router.get("/me", response_model=MaturityAssessmentDetailResponse)
async def get_my_assessment(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MaturityAssessmentDetailResponse:
    """현재 사용자의 최근 성숙도 평가 결과 조회."""
    service = MaturityService(db)
    assessment = await service.get_latest_assessment(user.id)  # type: ignore[arg-type]
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="성숙도 평가 기록이 없습니다",
        )
    return MaturityAssessmentDetailResponse.model_validate(assessment)
