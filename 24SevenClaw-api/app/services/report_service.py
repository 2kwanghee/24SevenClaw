from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.artifact import Artifact, ArtifactEvent
from app.models.orchestrator import OrchestratorSession, PhaseEvent, SubTask
from app.models.project import Project
from app.models.review_pipeline import ReviewRound
from app.schemas.report import (
    AITeamActivity,
    ArtifactStatusCount,
    PhaseTimelineEntry,
    ProjectReportResponse,
    QualityMetrics,
)

# 산출물 상태 전체 목록 (고정 순서)
ALL_ARTIFACT_STATUSES = [
    "draft",
    "reviewed",
    "revised",
    "approved",
    "in_development",
    "validated",
    "released",
]


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_project_report(
        self, project_id: UUID, owner_id: UUID
    ) -> ProjectReportResponse:
        """프로젝트 리포트 집계 — 산출물·타임라인·품질·AI 활동."""
        project = await self._get_project(project_id, owner_id)

        artifact_counts = await self._aggregate_artifact_statuses(project_id)
        phase_timeline = await self._build_phase_timeline(project_id)
        quality = await self._calculate_quality_metrics(project_id)
        activities = await self._collect_ai_team_activities(project_id)
        sessions_total, subtasks_total = await self._count_sessions_and_subtasks(
            project_id
        )

        return ProjectReportResponse(
            project_id=project.id,
            project_name=project.name,
            project_status=project.status,
            artifact_status_counts=artifact_counts,
            phase_timeline=phase_timeline,
            quality_metrics=quality,
            ai_team_activities=activities,
            sessions_total=sessions_total,
            subtasks_total=subtasks_total,
            generated_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    async def _get_project(self, project_id: UUID, owner_id: UUID) -> Project:
        project = await self.db.get(Project, project_id)
        if project is None:
            raise AppError("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다.", 404)
        if project.owner_id != owner_id:
            raise AppError("FORBIDDEN", "이 프로젝트에 접근할 수 없습니다.", 403)
        return project

    async def _aggregate_artifact_statuses(
        self, project_id: UUID
    ) -> list[ArtifactStatusCount]:
        stmt = (
            select(Artifact.status, func.count().label("cnt"))
            .where(Artifact.project_id == project_id)
            .group_by(Artifact.status)
        )
        result = await self.db.execute(stmt)
        counts_map: dict[str, int] = {}
        for row in result.all():
            counts_map[row.status] = row.cnt

        # 모든 상태를 포함하되 0도 표시
        return [
            ArtifactStatusCount(status=s, count=counts_map.get(s, 0))
            for s in ALL_ARTIFACT_STATUSES
        ]

    async def _build_phase_timeline(
        self, project_id: UUID
    ) -> list[PhaseTimelineEntry]:
        # 프로젝트의 모든 세션에서 PhaseEvent 조회
        stmt = (
            select(PhaseEvent)
            .join(
                OrchestratorSession,
                PhaseEvent.session_id == OrchestratorSession.id,
            )
            .where(OrchestratorSession.project_id == project_id)
            .order_by(PhaseEvent.created_at.asc())
        )
        result = await self.db.execute(stmt)
        events = list(result.scalars().all())

        entries: list[PhaseTimelineEntry] = []
        for i, ev in enumerate(events):
            # 다음 이벤트의 시간을 종료 시간으로 사용
            exited_at = events[i + 1].created_at if i + 1 < len(events) else None
            duration = None
            if exited_at is not None:
                duration = int((exited_at - ev.created_at).total_seconds())

            entries.append(
                PhaseTimelineEntry(
                    phase=ev.new_phase,
                    entered_at=ev.created_at,
                    exited_at=exited_at,
                    duration_seconds=duration,
                    actor_type=ev.actor_type,
                    message=ev.message,
                )
            )
        return entries

    async def _calculate_quality_metrics(
        self, project_id: UUID
    ) -> QualityMetrics:
        # 산출물 집계
        artifact_stmt = select(
            func.count().label("total"),
            func.count(
                case((Artifact.status == "released", Artifact.id), else_=None)
            ).label("released"),
            func.coalesce(func.avg(Artifact.revision_count), 0).label("avg_rev"),
        ).where(Artifact.project_id == project_id)
        art_row = (await self.db.execute(artifact_stmt)).one()

        # 리뷰 라운드 집계 (세션 경유)
        review_stmt = (
            select(
                func.count().label("total_rounds"),
                func.avg(ReviewRound.review_score).label("avg_score"),
                func.count(
                    case(
                        (ReviewRound.status == "merged", ReviewRound.id),
                        else_=None,
                    )
                ).label("merged"),
            )
            .join(
                OrchestratorSession,
                ReviewRound.session_id == OrchestratorSession.id,
            )
            .where(OrchestratorSession.project_id == project_id)
        )
        rev_row = (await self.db.execute(review_stmt)).one()

        total_rounds: int = rev_row.total_rounds or 0
        merged: int = rev_row.merged or 0
        completion_rate = (merged / total_rounds * 100) if total_rounds > 0 else 0.0

        return QualityMetrics(
            total_artifacts=art_row.total or 0,
            released_artifacts=art_row.released or 0,
            avg_review_score=(
                round(float(rev_row.avg_score), 1)
                if rev_row.avg_score is not None
                else None
            ),
            avg_revision_count=round(float(art_row.avg_rev), 1),
            review_rounds_total=total_rounds,
            review_completion_rate=round(completion_rate, 1),
        )

    async def _collect_ai_team_activities(
        self, project_id: UUID, limit: int = 50
    ) -> list[AITeamActivity]:
        """SubTask 상태 변경 + ArtifactEvent를 병합하여 최근 활동 목록 생성."""
        activities: list[AITeamActivity] = []

        # 1) SubTask 활동 (역할별)
        subtask_stmt = (
            select(SubTask)
            .join(
                OrchestratorSession,
                SubTask.session_id == OrchestratorSession.id,
            )
            .where(OrchestratorSession.project_id == project_id)
            .order_by(SubTask.updated_at.desc())
            .limit(limit)
        )
        subtask_result = await self.db.execute(subtask_stmt)
        for st in subtask_result.scalars().all():
            activities.append(
                AITeamActivity(
                    role=st.assigned_role,
                    title=st.title,
                    status=st.status,
                    event_type="subtask_update",
                    timestamp=st.updated_at,
                    message=st.result_summary,
                )
            )

        # 2) ArtifactEvent (에이전트 활동)
        artifact_evt_stmt = (
            select(ArtifactEvent)
            .join(Artifact, ArtifactEvent.artifact_id == Artifact.id)
            .where(
                Artifact.project_id == project_id,
                ArtifactEvent.actor_type == "agent",
            )
            .order_by(ArtifactEvent.created_at.desc())
            .limit(limit)
        )
        evt_result = await self.db.execute(artifact_evt_stmt)
        for ev in evt_result.scalars().all():
            activities.append(
                AITeamActivity(
                    role=ev.actor_type,
                    title=f"{ev.old_status} → {ev.new_status}",
                    status=ev.new_status or "",
                    event_type="artifact_transition",
                    timestamp=ev.created_at,
                    message=ev.message,
                )
            )

        # 시간 역순 정렬, 상위 limit개
        activities.sort(key=lambda a: a.timestamp, reverse=True)
        return activities[:limit]

    async def _count_sessions_and_subtasks(
        self, project_id: UUID
    ) -> tuple[int, int]:
        session_stmt = (
            select(func.count())
            .select_from(OrchestratorSession)
            .where(OrchestratorSession.project_id == project_id)
        )
        sessions = (await self.db.execute(session_stmt)).scalar_one()

        subtask_stmt = (
            select(func.count())
            .select_from(SubTask)
            .join(
                OrchestratorSession,
                SubTask.session_id == OrchestratorSession.id,
            )
            .where(OrchestratorSession.project_id == project_id)
        )
        subtasks = (await self.db.execute(subtask_stmt)).scalar_one()

        return sessions, subtasks
