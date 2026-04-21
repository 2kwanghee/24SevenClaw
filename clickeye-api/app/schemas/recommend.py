"""추천 엔진 API 스키마."""

from typing import Any

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    """추천 요청."""

    solution_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="솔루션 유형 (예: saas, rest-api, cli-tool, data-pipeline, mobile-app)",
    )


class RecommendResponse(BaseModel):
    """추천 응답."""

    solution_type: str
    agents: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    pipelines: list[dict[str, Any]]
    summary: str
