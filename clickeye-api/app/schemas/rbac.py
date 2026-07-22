from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

SystemRole = Literal["superadmin", "admin", "member", "viewer"]
OrgRole = Literal["org_admin", "org_member", "org_viewer"]
Permission = Literal[
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
]


class PermissionsResponse(BaseModel):
    permissions: list[str]
    system_role: str


class UserAdminResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    system_role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleUpdateRequest(BaseModel):
    system_role: SystemRole


class UserDeleteResponse(BaseModel):
    """사용자 삭제/비활성화 결과.

    - soft: is_active=False 로 비활성화 (레코드 보존)
    - hard: 레코드 물리 삭제 (superadmin 전용)
    """

    user_id: UUID
    mode: Literal["soft", "hard"]
    is_active: bool
    deleted: bool


class OrgMemberAddRequest(BaseModel):
    user_id: UUID
    org_role: OrgRole = "org_member"


class OrgMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    org_role: str
    invited_by: UUID | None
    joined_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: UUID
    actor_id: UUID
    target_user_id: UUID | None
    action: str
    old_value: str | None
    new_value: str
    resource: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    actor_id: UUID | None = None
    target_user_id: UUID | None = None
    action: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
