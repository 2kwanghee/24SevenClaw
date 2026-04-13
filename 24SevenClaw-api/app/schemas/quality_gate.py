"""품질 검증 게이트 스키마."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

QualityCheckCategory = Literal[
    "code_quality",
    "security",
    "performance",
    "test_coverage",
    "documentation",
]

QualityGateRunStatus = Literal["pending", "running", "passed", "failed"]

VerdictType = Literal["approved", "rejected"]


# === 검증 실행 ===


class QualityGateRunCreate(BaseModel):
    """품질 검증 실행 생성."""

    artifact_id: UUID | None = None
    threshold: int = Field(70, ge=0, le=100)


class QualityCheckSubmit(BaseModel):
    """QA 에이전트가 개별 검사 결과를 제출."""

    category: QualityCheckCategory
    score: int = Field(..., ge=0, le=100)
    agent_id: str | None = Field(None, max_length=100)
    details: str | None = None
    findings: list[dict[str, str]] | None = None


class QualityGateEvaluateRequest(BaseModel):
    """검증 평가 요청 (모든 체크 제출 후 호출)."""

    auto_transition: bool = Field(
        True,
        description="통과/실패 시 오케스트레이터 상태 자동 전이 여부",
    )


# === 응답 ===


class QualityCheckResponse(BaseModel):
    id: UUID
    run_id: UUID
    category: str
    score: int
    passed: str
    agent_id: str | None
    details: str | None
    findings: list[dict[str, str]] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityGateRunResponse(BaseModel):
    id: UUID
    session_id: UUID
    artifact_id: UUID | None
    run_number: int
    status: str
    overall_score: int | None
    threshold: int
    checks_total: int
    checks_passed: int
    verdict: str | None
    verdict_reason: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class QualityGateRunListResponse(BaseModel):
    items: list[QualityGateRunResponse]
    total: int


class QualityGateReportResponse(BaseModel):
    """검증 결과 리포트."""

    run: QualityGateRunResponse
    checks: list[QualityCheckResponse]
    summary: dict[str, int]  # category → score


class QualityGateEventResponse(BaseModel):
    id: UUID
    run_id: UUID
    event_type: str
    actor_type: str
    actor_id: UUID | None
    message: str | None
    metadata_json: dict | None  # type: ignore[type-arg]
    created_at: datetime

    model_config = {"from_attributes": True}
