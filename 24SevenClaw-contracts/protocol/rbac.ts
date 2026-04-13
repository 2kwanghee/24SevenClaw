/**
 * 24SevenClaw RBAC (역할 기반 접근 제어) 타입 정의
 * 시스템 역할 + 조직 역할 + 권한 매핑
 */

// === 시스템 역할 ===

export type SystemRole = 'superadmin' | 'admin' | 'member' | 'viewer';

// === 조직 역할 ===

export type OrgRole = 'org_admin' | 'org_member' | 'org_viewer';

// === 권한 ===

export type Permission =
  | 'project:create'
  | 'project:read'
  | 'project:update'
  | 'project:delete'
  | 'preset:manage'
  | 'contract:manage'
  | 'user:manage'
  | 'org:manage'
  | 'report:view'
  | 'rbac:manage';

// === 역할별 권한 매핑 ===

export const ROLE_PERMISSIONS: Record<SystemRole, Permission[]> = {
  superadmin: [
    'project:create', 'project:read', 'project:update', 'project:delete',
    'preset:manage', 'contract:manage', 'user:manage', 'org:manage',
    'report:view', 'rbac:manage',
  ],
  admin: [
    'project:create', 'project:read', 'project:update', 'project:delete',
    'preset:manage', 'contract:manage', 'user:manage', 'org:manage',
    'report:view',
  ],
  member: [
    'project:create', 'project:read', 'project:update', 'project:delete',
    'report:view',
  ],
  viewer: [
    'project:read',
    'report:view',
  ],
};

// === 조직 멤버십 ===

export interface OrganizationMembership {
  id: string;
  user_id: string;
  organization_id: string;
  org_role: OrgRole;
  invited_by: string | null;
  joined_at: string;
  is_active: boolean;
}

// === 역할 감사 로그 ===

export interface RoleAuditEntry {
  id: string;
  actor_id: string;
  target_user_id: string | null;
  action: string;
  old_value: string | null;
  new_value: string;
  resource: string | null;
  created_at: string;
}
