"""솔루션 유형 기반 추천 엔드포인트."""

from fastapi import APIRouter

from app.schemas.recommend import RecommendRequest, RecommendResponse
from app.services.recommend_service import RecommendService

router = APIRouter(prefix="/recommend", tags=["recommend"])

_service = RecommendService()


@router.post("", response_model=RecommendResponse)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    """솔루션 유형에 맞는 에이전트, 스킬, 파이프라인을 추천한다."""
    result = _service.recommend(request.solution_type)
    return RecommendResponse(**result)
