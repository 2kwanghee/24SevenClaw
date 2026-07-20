from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.orchestrator import OrchestratorSession
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User


class ControlTowerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_customers(
        self,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> tuple[list[dict], int]:
        """고객사 목록 + 집계 (프로젝트 수, 활성 세션 수)."""
        conditions = [Organization.org_type == "customer"]
        if status_filter:
            conditions.append(Organization.customer_status == status_filter)
        if search:
            conditions.append(Organization.company_name.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(Organization).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar_one()

        orgs_result = await self.db.execute(
            select(Organization)
            .where(*conditions)
            .order_by(Organization.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        orgs = list(orgs_result.scalars().all())

        items = []
        for org in orgs:
            # 프로젝트 수
            proj_count = (
                await self.db.execute(
                    select(func.count())
                    .select_from(Project)
                    .where(
                        Project.organization_id == org.id,
                        Project.status != "deleted",
                    )
                )
            ).scalar_one()

            # 활성 세션 수 (project → session 조인)
            active_session_count = (
                await self.db.execute(
                    select(func.count())
                    .select_from(OrchestratorSession)
                    .join(Project, OrchestratorSession.project_id == Project.id)
                    .where(
                        Project.organization_id == org.id,
                        OrchestratorSession.phase.notin_(["completed", "cancelled"]),
                    )
                )
            ).scalar_one()

            manager_name: str | None = None
            if org.account_manager_id:
                mgr = await self.db.get(User, org.account_manager_id)
                if mgr:
                    manager_name = mgr.display_name or mgr.email

            items.append(
                {
                    "id": org.id,
                    "company_name": org.company_name,
                    "org_type": org.org_type,
                    "customer_status": org.customer_status,
                    "account_manager_id": org.account_manager_id,
                    "account_manager_name": manager_name,
                    "project_count": proj_count,
                    "active_session_count": active_session_count,
                    "created_at": org.created_at,
                }
            )

        return items, int(total)

    async def get_customer(self, org_id: UUID) -> dict:
        """고객사 상세."""
        org = await self.db.get(Organization, org_id)
        if org is None or org.org_type != "customer":
            raise AppError("CUSTOMER_NOT_FOUND", "고객사를 찾을 수 없습니다", 404)

        manager_name: str | None = None
        if org.account_manager_id:
            mgr = await self.db.get(User, org.account_manager_id)
            if mgr:
                manager_name = mgr.display_name or mgr.email

        return {
            "id": org.id,
            "company_name": org.company_name,
            "org_type": org.org_type,
            "customer_status": org.customer_status,
            "account_manager_id": org.account_manager_id,
            "account_manager_name": manager_name,
            "size": org.size,
            "industry": org.industry,
            "main_product": org.main_product,
            "business_type": org.business_type,
            "company_description": org.company_description,
            "features": org.features or {},
            "created_at": org.created_at,
            "updated_at": org.updated_at,
        }

    async def list_customer_projects(
        self,
        org_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        """고객사의 프로젝트 목록."""
        org = await self.db.get(Organization, org_id)
        if org is None or org.org_type != "customer":
            raise AppError("CUSTOMER_NOT_FOUND", "고객사를 찾을 수 없습니다", 404)

        conditions = [
            Project.organization_id == org_id,
            Project.status != "deleted",
        ]

        total = (
            await self.db.execute(select(func.count()).select_from(Project).where(*conditions))
        ).scalar_one()

        projects_result = await self.db.execute(
            select(Project)
            .where(*conditions)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        projects = list(projects_result.scalars().all())

        items = []
        for proj in projects:
            owner = await self.db.get(User, proj.owner_id)
            owner_name = (owner.display_name or owner.email) if owner else None

            session_count = (
                await self.db.execute(
                    select(func.count())
                    .select_from(OrchestratorSession)
                    .where(OrchestratorSession.project_id == proj.id)
                )
            ).scalar_one()

            active_session_count = (
                await self.db.execute(
                    select(func.count())
                    .select_from(OrchestratorSession)
                    .where(
                        OrchestratorSession.project_id == proj.id,
                        OrchestratorSession.phase.notin_(["completed", "cancelled"]),
                    )
                )
            ).scalar_one()

            items.append(
                {
                    "id": proj.id,
                    "name": proj.name,
                    "slug": proj.slug,
                    "status": proj.status,
                    "project_type": proj.project_type,
                    "owner_id": proj.owner_id,
                    "owner_name": owner_name,
                    "organization_id": proj.organization_id,
                    "session_count": session_count,
                    "active_session_count": active_session_count,
                    "created_at": proj.created_at,
                    "updated_at": proj.updated_at,
                }
            )

        return items, int(total)

    async def get_project_overview(self, project_id: UUID) -> dict:
        """프로젝트 종합 정보."""
        proj = await self.db.get(Project, project_id)
        if proj is None or proj.status == "deleted":
            raise AppError("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다", 404)

        owner = await self.db.get(User, proj.owner_id)
        owner_name = (owner.display_name or owner.email) if owner else None

        session_count = (
            await self.db.execute(
                select(func.count())
                .select_from(OrchestratorSession)
                .where(OrchestratorSession.project_id == project_id)
            )
        ).scalar_one()

        active_session_count = (
            await self.db.execute(
                select(func.count())
                .select_from(OrchestratorSession)
                .where(
                    OrchestratorSession.project_id == project_id,
                    OrchestratorSession.phase.notin_(["completed", "cancelled"]),
                )
            )
        ).scalar_one()

        return {
            "id": proj.id,
            "name": proj.name,
            "slug": proj.slug,
            "status": proj.status,
            "project_type": proj.project_type,
            "owner_id": proj.owner_id,
            "owner_name": owner_name,
            "organization_id": proj.organization_id,
            "session_count": session_count,
            "active_session_count": active_session_count,
            "created_at": proj.created_at,
            "updated_at": proj.updated_at,
        }

    async def set_customer_status(self, org_id: UUID, new_status: str) -> dict:
        """고객사 상태 변경 (active | paused | archived)."""
        org = await self.db.get(Organization, org_id)
        if org is None or org.org_type != "customer":
            raise AppError("CUSTOMER_NOT_FOUND", "고객사를 찾을 수 없습니다", 404)

        org.customer_status = new_status  # type: ignore[assignment]
        org.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(org)
        return await self.get_customer(org_id)

    async def set_org_feature(self, org_id: UUID, feature_name: str, value: bool) -> dict:
        """조직 기능 플래그 설정."""
        org = await self.db.get(Organization, org_id)
        if org is None or org.org_type != "customer":
            raise AppError("CUSTOMER_NOT_FOUND", "고객사를 찾을 수 없습니다", 404)

        current: dict = dict(org.features or {})
        current[feature_name] = value
        org.features = current  # type: ignore[assignment]
        org.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        return await self.get_customer(org_id)

    async def transfer_project(self, project_id: UUID, to_org_id: UUID) -> dict:
        """프로젝트를 다른 고객사로 이동."""
        proj = await self.db.get(Project, project_id)
        if proj is None or proj.status == "deleted":
            raise AppError("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다", 404)

        target_org = await self.db.get(Organization, to_org_id)
        if target_org is None:
            raise AppError("ORGANIZATION_NOT_FOUND", "대상 고객사를 찾을 수 없습니다", 404)

        proj.organization_id = to_org_id  # type: ignore[assignment]
        proj.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        return await self.get_project_overview(project_id)
