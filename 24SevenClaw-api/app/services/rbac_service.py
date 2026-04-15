from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.rbac import OrganizationMembership, RoleAuditLog
from app.models.user import User

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "superadmin": [
        "project:create", "project:read", "project:update", "project:delete",
        "preset:manage", "contract:manage", "user:manage", "org:manage",
        "report:view", "rbac:manage", "platform:view",
    ],
    "admin": [
        "project:create", "project:read", "project:update", "project:delete",
        "preset:manage", "contract:manage", "user:manage", "org:manage",
        "report:view",
    ],
    "member": [
        "project:create", "project:read", "project:update", "project:delete",
        "report:view",
    ],
    "viewer": [
        "project:read",
        "report:view",
    ],
}

VALID_SYSTEM_ROLES = {"superadmin", "admin", "member", "viewer"}
VALID_ORG_ROLES = {"org_admin", "org_member", "org_viewer"}


class RBACService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def check_permission(self, user: User, permission: str) -> bool:
        """사용자의 시스템 역할로 권한 확인."""
        role = getattr(user, "system_role", "member") or "member"
        permissions = ROLE_PERMISSIONS.get(role, [])
        return permission in permissions

    def get_permissions(self, user: User) -> list[str]:
        """사용자의 권한 목록 반환."""
        role = getattr(user, "system_role", "member") or "member"
        return ROLE_PERMISSIONS.get(role, [])

    async def assign_system_role(
        self,
        target_user_id: UUID,
        role: str,
        actor: User,
    ) -> User:
        """시스템 역할 변경 (superadmin만 가능)."""
        if not self.check_permission(actor, "rbac:manage"):
            raise AppError("FORBIDDEN", "RBAC 관리 권한이 없습니다", 403)

        if role not in VALID_SYSTEM_ROLES:
            raise AppError("INVALID_ROLE", f"유효하지 않은 역할입니다: {role}", 400)

        target = await self.db.get(User, target_user_id)
        if target is None:
            raise AppError("USER_NOT_FOUND", "사용자를 찾을 수 없습니다", 404)

        old_role = target.system_role or "member"
        target.system_role = role  # type: ignore[assignment]

        # 감사 로그 기록
        audit = RoleAuditLog(
            actor_id=actor.id,
            target_user_id=target_user_id,
            action="assign_system_role",
            old_value=old_role,
            new_value=role,
            resource="system_role",
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def list_users(self, actor: User) -> list[User]:
        """전체 사용자 목록 (superadmin 전용)."""
        if not self.check_permission(actor, "user:manage"):
            raise AppError("FORBIDDEN", "사용자 관리 권한이 없습니다", 403)

        result = await self.db.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def add_org_member(
        self,
        organization_id: UUID,
        user_id: UUID,
        org_role: str,
        actor: User,
    ) -> OrganizationMembership:
        """조직에 멤버 추가."""
        if not self.check_permission(actor, "org:manage"):
            raise AppError("FORBIDDEN", "조직 관리 권한이 없습니다", 403)

        if org_role not in VALID_ORG_ROLES:
            raise AppError("INVALID_ROLE", f"유효하지 않은 조직 역할입니다: {org_role}", 400)

        # 이미 멤버인지 확인
        existing = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.is_active == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise AppError("ALREADY_MEMBER", "이미 조직의 멤버입니다", 409)

        membership = OrganizationMembership(
            user_id=user_id,
            organization_id=organization_id,
            org_role=org_role,
            invited_by=actor.id,
        )
        self.db.add(membership)

        # 감사 로그
        audit = RoleAuditLog(
            actor_id=actor.id,
            target_user_id=user_id,
            action="add_org_member",
            old_value=None,
            new_value=org_role,
            resource=f"organization:{organization_id}",
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def remove_org_member(
        self,
        organization_id: UUID,
        user_id: UUID,
        actor: User,
    ) -> None:
        """조직에서 멤버 제거 (비활성화)."""
        if not self.check_permission(actor, "org:manage"):
            raise AppError("FORBIDDEN", "조직 관리 권한이 없습니다", 403)

        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.is_active == True,  # noqa: E712
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            raise AppError("NOT_MEMBER", "조직의 멤버가 아닙니다", 404)

        membership.is_active = False  # type: ignore[assignment]

        # 감사 로그
        audit = RoleAuditLog(
            actor_id=actor.id,
            target_user_id=user_id,
            action="remove_org_member",
            old_value=membership.org_role,
            new_value="removed",
            resource=f"organization:{organization_id}",
        )
        self.db.add(audit)
        await self.db.commit()

    async def get_org_members(
        self,
        organization_id: UUID,
        actor: User,
    ) -> list[OrganizationMembership]:
        """조직 멤버 목록 조회."""
        if not self.check_permission(actor, "org:manage"):
            raise AppError("FORBIDDEN", "조직 관리 권한이 없습니다", 403)

        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.is_active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def list_role_audit(
        self,
        actor: User,
        actor_id: UUID | None = None,
        target_user_id: UUID | None = None,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RoleAuditLog]:
        """감사 로그 조회 (admin 이상)."""
        if not self.check_permission(actor, "user:manage"):
            raise AppError("FORBIDDEN", "감사 로그 조회 권한이 없습니다", 403)

        query = select(RoleAuditLog).order_by(RoleAuditLog.created_at.desc())

        if actor_id is not None:
            query = query.where(RoleAuditLog.actor_id == actor_id)
        if target_user_id is not None:
            query = query.where(RoleAuditLog.target_user_id == target_user_id)
        if action is not None:
            query = query.where(RoleAuditLog.action == action)

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())
