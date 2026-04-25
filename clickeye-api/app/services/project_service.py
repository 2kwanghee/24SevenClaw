import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.wizard_config import WizardConfigSave
from app.services.base import BaseService
from app.utils.db import get_or_404


def _slugify(text: str) -> str:
    """간단한 slug 생성: 소문자 + 하이픈."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


class ProjectService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create(self, owner_id: UUID, data: ProjectCreate) -> Project:
        slug = _slugify(data.name)

        # slug 중복 시 숫자 접미사 추가
        base_slug = slug
        counter = 1
        while True:
            stmt = select(Project).where(
                Project.owner_id == owner_id, Project.slug == slug
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project(
            owner_id=owner_id,
            name=data.name,
            slug=slug,
            description=data.description,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_by_id(self, project_id: UUID, owner_id: UUID) -> Project:
        return await get_or_404(
            self.db,
            Project,
            Project.id == project_id,
            Project.owner_id == owner_id,
            code="PROJECT_NOT_FOUND",
            message="프로젝트를 찾을 수 없습니다",
        )

    async def list_by_owner(
        self,
        owner_id: UUID,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> tuple[list[Project], int]:
        # 기본 조건: 소유자 + 삭제되지 않은 것
        conditions = [Project.owner_id == owner_id, Project.status != "deleted"]

        # 상태 필터 (active/archived)
        if status_filter in ("active", "archived"):
            conditions.append(Project.status == status_filter)

        # 이름 검색 (ILIKE)
        if search:
            conditions.append(Project.name.ilike(f"%{search}%"))

        # 총 개수
        count_stmt = (
            select(func.count())
            .select_from(Project)
            .where(*conditions)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        # 목록 조회
        stmt = (
            select(Project)
            .where(*conditions)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        projects = list(result.scalars().all())
        return projects, int(total)

    async def update(
        self, project_id: UUID, owner_id: UUID, data: ProjectUpdate
    ) -> Project:
        project = await self.get_by_id(project_id, owner_id)

        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            update_data["slug"] = _slugify(str(update_data["name"]))

        for key, value in update_data.items():
            setattr(project, key, value)

        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: UUID, owner_id: UUID) -> None:
        project = await self.get_by_id(project_id, owner_id)
        project.status = "deleted"  # type: ignore[assignment]
        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()

    async def save_wizard_config(
        self, project_id: UUID, owner_id: UUID, data: WizardConfigSave
    ) -> Project:
        project = await self.get_by_id(project_id, owner_id)
        project.wizard_data = data.wizard_data.model_dump()  # type: ignore[assignment]
        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_wizard_config(self, project_id: UUID, owner_id: UUID) -> Project:
        return await self.get_by_id(project_id, owner_id)

    async def get_for_admin(self, project_id: UUID) -> Project:
        """관리자 전용 — owner 체크 없이 프로젝트 조회."""
        return await get_or_404(
            self.db,
            Project,
            Project.id == project_id,
            Project.status != "deleted",
            code="PROJECT_NOT_FOUND",
            message="프로젝트를 찾을 수 없습니다",
        )
