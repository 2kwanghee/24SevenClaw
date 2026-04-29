from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.rbac import (
    AuditLogResponse,
    OrgMemberAddRequest,
    OrgMemberResponse,
    PermissionsResponse,
    RoleUpdateRequest,
    UserAdminResponse,
)
from app.services.rbac_service import RBACService

router = APIRouter()


# --- 내 권한 ---


@router.get("/rbac/permissions", response_model=PermissionsResponse, tags=["rbac"])
async def get_my_permissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PermissionsResponse:
    """현재 사용자의 권한 목록 조회."""
    service = RBACService(db)
    permissions = service.get_permissions(user)
    return PermissionsResponse(
        permissions=permissions,
        system_role=user.system_role or "member",
    )


# --- 관리자 전용: 사용자 관리 ---


@router.get("/admin/users", response_model=list[UserAdminResponse], tags=["admin"])
async def list_users(
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
) -> list[UserAdminResponse]:
    """전체 사용자 목록 (admin 이상)."""
    service = RBACService(db)
    users = await service.list_users(user)
    return [UserAdminResponse.model_validate(u) for u in users]


@router.patch(
    "/admin/users/{user_id}/role",
    response_model=UserAdminResponse,
    tags=["admin"],
)
async def update_user_role(
    user_id: UUID,
    data: RoleUpdateRequest,
    user: User = Depends(require_permission("rbac:manage")),
    db: AsyncSession = Depends(get_db),
) -> UserAdminResponse:
    """사용자 역할 변경 (superadmin만 가능)."""
    service = RBACService(db)
    updated = await service.assign_system_role(user_id, data.system_role, user)
    return UserAdminResponse.model_validate(updated)


# --- 조직 멤버 관리 ---


@router.get(
    "/organizations/{org_id}/members",
    response_model=list[OrgMemberResponse],
    tags=["organizations"],
)
async def get_org_members(
    org_id: UUID,
    user: User = Depends(require_permission("org:manage")),
    db: AsyncSession = Depends(get_db),
) -> list[OrgMemberResponse]:
    """조직 멤버 목록 조회."""
    service = RBACService(db)
    members = await service.get_org_members(org_id, user)
    return [OrgMemberResponse.model_validate(m) for m in members]


@router.post(
    "/organizations/{org_id}/members",
    response_model=OrgMemberResponse,
    status_code=201,
    tags=["organizations"],
)
async def add_org_member(
    org_id: UUID,
    data: OrgMemberAddRequest,
    user: User = Depends(require_permission("org:manage")),
    db: AsyncSession = Depends(get_db),
) -> OrgMemberResponse:
    """조직에 멤버 추가."""
    service = RBACService(db)
    membership = await service.add_org_member(org_id, data.user_id, data.org_role, user)
    return OrgMemberResponse.model_validate(membership)


@router.delete(
    "/organizations/{org_id}/members/{user_id}",
    status_code=204,
    tags=["organizations"],
)
async def remove_org_member(
    org_id: UUID,
    user_id: UUID,
    user: User = Depends(require_permission("org:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """조직에서 멤버 제거."""
    service = RBACService(db)
    await service.remove_org_member(org_id, user_id, user)


# --- 감사 로그 ---


@router.get("/admin/audit-log", response_model=list[AuditLogResponse], tags=["admin"])
async def get_audit_log(
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
    actor_id: UUID | None = Query(None),
    target_user_id: UUID | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[AuditLogResponse]:
    """감사 로그 조회 (admin 이상)."""
    service = RBACService(db)
    logs = await service.list_role_audit(
        actor=user,
        actor_id=actor_id,
        target_user_id=target_user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return [AuditLogResponse.model_validate(log) for log in logs]
