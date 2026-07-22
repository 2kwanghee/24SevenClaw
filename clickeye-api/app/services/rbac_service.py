from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.project import Project
from app.models.rbac import OrganizationMembership, RoleAuditLog
from app.models.user import User

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "superadmin": [
        "project:create",
        "project:read",
        "project:update",
        "project:delete",
        "preset:manage",
        "contract:manage",
        "user:manage",
        "org:manage",
        "report:view",
        "rbac:manage",
        "platform:view",
        "pm:manage",
        "registry:manage",
        "prototype:manage",
        "settings:manage",
        "control_tower:read",
        "control_tower:write",
    ],
    "admin": [
        "project:create",
        "project:read",
        "project:update",
        "project:delete",
        "preset:manage",
        "contract:manage",
        "user:manage",
        "org:manage",
        "report:view",
        "pm:manage",
        "registry:manage",
        "prototype:manage",
        "settings:manage",
        "control_tower:read",
        "control_tower:write",
    ],
    "member": [
        "project:create",
        "project:read",
        "project:update",
        "project:delete",
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

    async def _count_superadmins(self) -> int:
        """전체 superadmin 수를 반환."""
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.system_role == "superadmin")
        )
        return int(result.scalar_one())

    async def delete_user(
        self,
        target_user_id: UUID,
        actor: User,
        hard: bool = False,
    ) -> str:
        """사용자 삭제.

        - soft(기본): is_active=False 로 비활성화 (admin 이상). 레코드/연관 데이터 보존.
        - hard: 레코드 물리 삭제 (superadmin 전용). FK 연쇄 안전 처리.

        반환값: "soft" | "hard" (수행한 모드).

        가드:
        - 자기 자신 삭제 금지 (400)
        - superadmin 대상은 superadmin 만 삭제 가능 (403)
        - 마지막 남은 superadmin 삭제 금지 (409)
        - hard 삭제는 superadmin 전용 (403)
        - 조직 스코프: 비-superadmin actor 는 동일 조직 사용자만 삭제 (403)

        hard 삭제 FK 처리:
        - owner_id 로 활성(비-deleted) 프로젝트를 보유하면 차단(409) — 파괴적 연쇄 방지.
          (프로젝트를 먼저 삭제/이관해야 함)
        - role_audit_logs.actor_id 는 ondelete=SET NULL 이나 NOT NULL 컬럼이라
          PG 에서 위반이 발생하므로, 해당 actor 로그를 명시적으로 선삭제한다.
        - 그 외 CASCADE FK(pm_ratings, organization_memberships, *_credentials,
          maturity_assessments)와 SET NULL FK(orchestrator.created_by, ticket 등)는
          기존 ondelete 제약으로 DB 가 정합 처리한다.
        """
        # 권한: soft 는 user:manage(admin+), hard 는 superadmin 전용
        if not self.check_permission(actor, "user:manage"):
            raise AppError("FORBIDDEN", "사용자 관리 권한이 없습니다", 403)

        actor_is_superadmin = (getattr(actor, "system_role", "") or "") == "superadmin"
        if hard and not actor_is_superadmin:
            raise AppError("FORBIDDEN", "하드 삭제는 superadmin 만 가능합니다", 403)

        target = await self.db.get(User, target_user_id)
        if target is None:
            raise AppError("USER_NOT_FOUND", "사용자를 찾을 수 없습니다", 404)

        target_role = target.system_role or "member"

        # superadmin 대상은 superadmin 만 삭제 가능
        if target_role == "superadmin" and not actor_is_superadmin:
            raise AppError("FORBIDDEN", "superadmin 사용자는 superadmin 만 삭제할 수 있습니다", 403)

        # 마지막 남은 superadmin 삭제/비활성화 금지
        # (self-delete 검사보다 먼저 — 단일 superadmin 자기 삭제도 여기서 차단)
        if target_role == "superadmin" and await self._count_superadmins() <= 1:
            raise AppError("LAST_SUPERADMIN", "마지막 superadmin 은 삭제할 수 없습니다", 409)

        # 자기 자신 삭제 금지
        if target.id == actor.id:
            raise AppError("CANNOT_DELETE_SELF", "자기 자신은 삭제할 수 없습니다", 400)

        # 조직 스코프: 비-superadmin actor 는 동일 조직 사용자만
        if not actor_is_superadmin and target.organization_id != actor.organization_id:
            raise AppError("FORBIDDEN", "다른 조직의 사용자를 삭제할 수 없습니다", 403)

        if not hard:
            # 소프트 삭제: 비활성화
            target.is_active = False  # type: ignore[assignment]
            audit = RoleAuditLog(
                actor_id=actor.id,
                target_user_id=target_user_id,
                action="deactivate_user",
                old_value=target_role,
                new_value="inactive",
                resource="user",
            )
            self.db.add(audit)
            await self.db.commit()
            return "soft"

        # 하드 삭제 (superadmin)
        # 활성 프로젝트 소유 시 차단 (파괴적 연쇄 방지)
        active_projects = await self.db.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.owner_id == target_user_id, Project.status != "deleted")
        )
        if int(active_projects.scalar_one()) > 0:
            raise AppError(
                "USER_HAS_PROJECTS",
                "소유한 프로젝트가 있어 삭제할 수 없습니다. 프로젝트를 먼저 삭제/이관하세요",
                409,
            )

        # role_audit_logs.actor_id (NOT NULL + SET NULL) 위반 회피: actor 로그 선삭제
        await self.db.execute(delete(RoleAuditLog).where(RoleAuditLog.actor_id == target_user_id))
        await self.db.delete(target)
        await self.db.commit()
        return "hard"

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
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.is_active == True,  # noqa: E712
            )
            .limit(1)
        )
        # 활성 멤버십 중복 행이 있어도 500 나지 않도록 first() 사용
        if existing.scalars().first() is not None:
            raise AppError("ALREADY_MEMBER", "이미 조직의 멤버입니다", 409)

        membership = OrganizationMembership(
            user_id=user_id,
            organization_id=organization_id,
            org_role=org_role,
            invited_by=actor.id,
        )
        self.db.add(membership)

        # desync 봉합: 대상 유저의 primary organization_id가 없으면 이 org로 설정
        target_user = await self.db.get(User, user_id)
        if target_user is not None and target_user.organization_id is None:
            target_user.organization_id = organization_id

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
