from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert(self, user_id: UUID, data: OrganizationCreate) -> Organization:
        """회사 정보를 등록하거나 수정한다 (upsert)."""
        user = await self.db.get(User, user_id)
        if user is None:
            raise AppError("USER_NOT_FOUND", "사용자를 찾을 수 없습니다", 404)

        org_id = user.organization_id  # type: ignore[attr-defined]

        if org_id is not None:
            # 기존 조직 수정
            org = await self.db.get(Organization, org_id)
            if org is None:
                raise AppError("ORGANIZATION_NOT_FOUND", "조직을 찾을 수 없습니다", 404)

            org.company_name = data.company_name  # type: ignore[assignment]
            org.size = data.size  # type: ignore[assignment]
            org.industry = data.industry  # type: ignore[assignment]
            org.tech_stack = data.tech_stack  # type: ignore[assignment]
            org.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        else:
            # 새 조직 생성
            org = Organization(
                company_name=data.company_name,
                size=data.size,
                industry=data.industry,
                tech_stack=data.tech_stack,
            )
            self.db.add(org)
            await self.db.flush()

            # User에 organization_id 연결
            user.organization_id = org.id  # type: ignore[attr-defined]

        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_by_user(self, user_id: UUID) -> Organization:
        """현재 사용자의 회사 정보를 조회한다."""
        user = await self.db.get(User, user_id)
        if user is None:
            raise AppError("USER_NOT_FOUND", "사용자를 찾을 수 없습니다", 404)

        org_id = user.organization_id  # type: ignore[attr-defined]
        if org_id is None:
            raise AppError("ORGANIZATION_NOT_FOUND", "등록된 회사 정보가 없습니다", 404)

        stmt = select(Organization).where(Organization.id == org_id)
        result = await self.db.execute(stmt)
        org = result.scalar_one_or_none()
        if org is None:
            raise AppError("ORGANIZATION_NOT_FOUND", "조직을 찾을 수 없습니다", 404)
        return org
