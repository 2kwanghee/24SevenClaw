from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# === 산출물 상태별 카운트 ===


class ArtifactStatusCount(BaseModel):
    status: str
    count: int


# === 단계 타임라인 ===


class PhaseTimelineEntry(BaseModel):
    phase: str
    entered_at: datetime
    exited_at: datetime | None = None
    duration_seconds: int | None = None
    actor_type: str | None = None
    message: str | None = None


# === 품질 메트릭 ===


class QualityMetrics(BaseModel):
    total_artifacts: int
    released_artifacts: int
    avg_review_score: float | None = None
    avg_revision_count: float
    review_rounds_total: int
    review_completion_rate: float


# === AI 팀 활동 ===


class AITeamActivity(BaseModel):
    role: str
    title: str
    status: str
    event_type: str
    timestamp: datetime
    message: str | None = None


# === 프로젝트 리포트 응답 ===


class ProjectReportResponse(BaseModel):
    project_id: UUID
    project_name: str
    project_status: str
    artifact_status_counts: list[ArtifactStatusCount]
    phase_timeline: list[PhaseTimelineEntry]
    quality_metrics: QualityMetrics
    ai_team_activities: list[AITeamActivity]
    sessions_total: int
    subtasks_total: int
    generated_at: datetime
