"use client";

import { Suspense, useState } from "react";
import { Shield, Users, ChevronDown } from "lucide-react";
import { toast } from "sonner";

import { RoleGuard } from "@/components/common/role-guard";
import { useAdminUsers, useUpdateUserRole } from "@/hooks/use-rbac";
import type { SystemRole, UserAdminResponse } from "@/lib/api-client";

const ROLE_LABELS: Record<SystemRole, string> = {
  superadmin: "슈퍼 관리자",
  admin: "관리자",
  member: "멤버",
  viewer: "뷰어",
};

const ROLE_COLORS: Record<SystemRole, string> = {
  superadmin: "bg-red-50 text-red-700 border-red-200",
  admin: "bg-violet-50 text-violet-700 border-violet-200",
  member: "bg-blue-50 text-blue-700 border-blue-200",
  viewer: "bg-zinc-100 text-[var(--text-muted)] border-[var(--border-subtle)]",
};

function RoleBadge({ role }: { role: SystemRole }) {
  return (
    <span
      className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-xs font-medium ${ROLE_COLORS[role]}`}
    >
      {ROLE_LABELS[role]}
    </span>
  );
}

interface RoleSelectProps {
  userId: string;
  currentRole: SystemRole;
}

function RoleSelect({ userId, currentRole }: RoleSelectProps) {
  const [open, setOpen] = useState(false);
  const updateRole = useUpdateUserRole();

  const handleSelect = (role: SystemRole) => {
    if (role === currentRole) {
      setOpen(false);
      return;
    }
    updateRole.mutate(
      { userId, data: { system_role: role } },
      {
        onSuccess: () => {
          toast.success(`역할이 ${ROLE_LABELS[role]}(으)로 변경되었습니다`);
          setOpen(false);
        },
        onError: (err) => {
          toast.error(err.message || "역할 변경에 실패했습니다");
          setOpen(false);
        },
      },
    );
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        disabled={updateRole.isPending}
        className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-zinc-400 hover:bg-[var(--bg-hover)] disabled:opacity-50"
      >
        {ROLE_LABELS[currentRole]}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-1 w-40 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1 shadow-xl">
            {(
              Object.entries(ROLE_LABELS) as [SystemRole, string][]
            ).map(([role, label]) => (
              <button
                key={role}
                type="button"
                onClick={() => handleSelect(role)}
                className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                  role === currentRole
                    ? "bg-[var(--bg-hover)] text-[var(--text-secondary)]"
                    : "text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function UserRow({ user }: { user: UserAdminResponse }) {
  const initials = user.display_name
    ? user.display_name.charAt(0).toUpperCase()
    : "U";

  return (
    <tr className="border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-hover)]">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-sm font-medium text-zinc-700">
            {initials}
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">
              {user.display_name}
            </p>
            <p className="text-xs text-[var(--text-muted)]">{user.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <RoleBadge role={user.system_role} />
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            user.is_active
              ? "bg-emerald-50 text-emerald-700"
              : "bg-zinc-100 text-[var(--text-muted)]"
          }`}
        >
          {user.is_active ? "활성" : "비활성"}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
        {new Date(user.created_at).toLocaleDateString("ko-KR")}
      </td>
      <td className="px-4 py-3 text-right">
        <RoleSelect userId={user.id} currentRole={user.system_role} />
      </td>
    </tr>
  );
}

function UsersContent() {
  const { data: users, isLoading, error } = useAdminUsers();

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
          <Users className="h-5 w-5 text-[var(--text-secondary)]" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">사용자 관리</h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            전체 사용자 목록과 역할을 관리합니다
          </p>
        </div>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-xl bg-[var(--bg-hover)]"
            />
          ))}
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          사용자 목록을 불러오지 못했습니다.
        </div>
      )}

      {/* 테이블 */}
      {users && (
        <>
          <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                    사용자
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                    역할
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                    상태
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                    가입일
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                    역할 변경
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <UserRow key={user.id} user={user} />
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
            총 {users.length}명
          </p>
        </>
      )}

      {/* 빈 상태 */}
      {users && users.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <Users className="h-12 w-12 text-[var(--text-muted)]" />
          <p className="text-sm text-[var(--text-muted)]">등록된 사용자가 없습니다</p>
        </div>
      )}
    </div>
  );
}

export default function AdminUsersPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <Suspense
        fallback={
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-16 animate-pulse rounded-xl bg-[var(--bg-hover)]"
              />
            ))}
          </div>
        }
      >
        <UsersContent />
      </Suspense>
    </RoleGuard>
  );
}
