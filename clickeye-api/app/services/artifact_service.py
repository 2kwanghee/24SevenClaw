from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.artifact import Artifact, ArtifactEvent
from app.schemas.artifact import ArtifactCreate, ArtifactTransitionRequest

# 허용된 상태 전이 맵 (contracts와 동기화)
ARTIFACT_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["reviewed"],
    "reviewed": ["revised", "approved"],
    "revised": ["reviewed"],
    "approved": ["in_development"],
    "in_development": ["validated"],
    "validated": ["released", "in_development"],
    "released": [],
}


class ArtifactService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, project_id: UUID, data: ArtifactCreate) -> Artifact:
        artifact = Artifact(
            project_id=project_id,
            name=data.name,
            description=data.description,
            artifact_type=data.artifact_type,
            status="draft",
            created_by_ai=data.created_by_ai,
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        return artifact

    async def get(self, artifact_id: UUID) -> Artifact:
        artifact = await self.db.get(Artifact, artifact_id)
        if artifact is None:
            raise AppError("ARTIFACT_NOT_FOUND", "산출물을 찾을 수 없습니다.", 404)
        return artifact

    async def list_by_project(
        self,
        project_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
    ) -> tuple[list[Artifact], int]:
        conditions = [Artifact.project_id == project_id]
        if status_filter:
            conditions.append(Artifact.status == status_filter)

        count_stmt = select(func.count()).select_from(Artifact).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Artifact)
            .where(*conditions)
            .order_by(Artifact.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        artifacts = list(result.scalars().all())
        return artifacts, total

    async def transition(
        self, artifact_id: UUID, data: ArtifactTransitionRequest
    ) -> tuple[Artifact, ArtifactEvent]:
        artifact = await self.get(artifact_id)
        old_status = artifact.status
        new_status = data.target_status

        # 전이 규칙 검증
        allowed = ARTIFACT_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            raise AppError(
                "INVALID_TRANSITION",
                f"'{old_status}' → '{new_status}' 전이는 허용되지 않습니다. 허용: {allowed}",
                422,
            )

        # 상태 업데이트
        artifact.status = new_status
        artifact.updated_at = datetime.now(UTC)

        # 메타정보 자동 기록
        if new_status == "reviewed" and data.actor_type == "agent":
            artifact.reviewed_by_ai = str(data.actor_id) if data.actor_id else "unknown"
        if new_status == "revised":
            artifact.revision_count += 1

        # 변경 이력 기록
        event = ArtifactEvent(
            artifact_id=artifact.id,
            event_type="status_transition",
            old_status=old_status,
            new_status=new_status,
            actor_type=data.actor_type,
            actor_id=data.actor_id,
            message=data.message,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(artifact)
        await self.db.refresh(event)
        return artifact, event

    async def bulk_transition(
        self,
        artifact_ids: list[UUID],
        target_status: str,
        actor_type: str,
        message: str | None = None,
    ) -> list[tuple[Artifact, ArtifactEvent]]:
        """여러 산출물의 상태를 일괄 전이한다.

        커밋은 호출자가 담당한다. 전이 불가한 산출물은 건너뛴다.
        """
        results: list[tuple[Artifact, ArtifactEvent]] = []
        for artifact_id in artifact_ids:
            artifact = await self.db.get(Artifact, artifact_id)
            if artifact is None:
                continue

            old_status = artifact.status
            allowed = ARTIFACT_TRANSITIONS.get(old_status, [])
            if target_status not in allowed:
                continue

            artifact.status = target_status
            artifact.updated_at = datetime.now(UTC)

            if target_status == "reviewed" and actor_type == "agent":
                artifact.reviewed_by_ai = "system"
            if target_status == "revised":
                artifact.revision_count += 1

            event = ArtifactEvent(
                artifact_id=artifact.id,
                event_type="status_transition",
                old_status=old_status,
                new_status=target_status,
                actor_type=actor_type,
                message=message,
            )
            self.db.add(event)
            results.append((artifact, event))

        return results

    async def get_history(self, artifact_id: UUID) -> list[ArtifactEvent]:
        # 산출물 존재 확인
        await self.get(artifact_id)

        stmt = (
            select(ArtifactEvent)
            .where(ArtifactEvent.artifact_id == artifact_id)
            .order_by(ArtifactEvent.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
