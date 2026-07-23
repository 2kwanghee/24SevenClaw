"use client";

import { Suspense, useRef, useState } from "react";
import { Users, ChevronDown, Ban, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { BentoCard } from "@/components/ui/bento";
import { RoleGuard } from "@/components/common/role-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { ConfirmByTypingDialog } from "@/components/common/confirm-by-typing-dialog";
import { useAdminUsers, useUpdateUserRole, useDeleteUser } from "@/hooks/use-rbac";
import { useMe } from "@/hooks/use-me";
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
  viewer: "bg-[var(--bg-base)] text-[var(--text-muted)] border-[var(--border-subtle)]",
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
  const [menuPos, setMenuPos] = useState({ top: 0, right: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);
  const updateRole = useUpdateUserRole();
  const tT = useTranslations("toast.users");

  const handleToggle = () => {
    if (!open && btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      setMenuPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
    }
    setOpen((v) => !v);
  };

  const handleSelect = (role: SystemRole) => {
    if (role === currentRole) {
      setOpen(false);
      return;
    }
    updateRole.mutate(
      { userId, data: { system_role: role } },
      {
        onSuccess: () => {
          toast.success(tT("roleChangeSuccess", { role: ROLE_LABELS[role] }));
          setOpen(false);
        },
        onError: (err) => {
          toast.error(err.message || tT("roleChangeFail"));
          setOpen(false);
        },
      },
    );
  };

  return (
    <div>
      <button
        ref={btnRef}
        type="button"
        onClick={handleToggle}
        disabled={updateRole.isPending}
        className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)] disabled:opacity-50"
      >
        {ROLE_LABELS[currentRole]}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div
            className="fixed z-50 w-40 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1 shadow-xl"
            style={{ top: menuPos.top, right: menuPos.right }}
          >
            {(Object.entries(ROLE_LABELS) as [SystemRole, string][]).map(([role, label]) => (
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

interface UserRowProps {
  user: UserAdminResponse;
  isSelf: boolean;
  isSuperadmin: boolean;
  onDeactivate: (user: UserAdminResponse) => void;
  onHardDelete: (user: UserAdminResponse) => void;
}

function UserRow({
  user,
  isSelf,
  isSuperadmin,
  onDeactivate,
  onHardDelete,
}: UserRowProps) {
  const initials = user.display_name
    ? user.display_name.charAt(0).toUpperCase()
    : "U";

  return (
    <tr className="border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-hover)]">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--bg-base)] text-sm font-medium text-[var(--text-secondary)]">
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
              : "bg-[var(--bg-base)] text-[var(--text-muted)]"
          }`}
        >
          {user.is_active ? "활성" : "비활성"}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
        {new Date(user.created_at).toLocaleDateString("ko-KR")}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-2">
          <RoleSelect userId={user.id} currentRole={user.system_role} />

          {/* 비활성화(소프트) — 활성 사용자 & 본인 아님 */}
          {user.is_active && !isSelf && (
            <button
              type="button"
              onClick={() => onDeactivate(user)}
              aria-label={`${user.display_name} 비활성화`}
              title="비활성화"
              className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-amber-300 hover:bg-amber-50 hover:text-amber-700"
            >
              <Ban className="h-3.5 w-3.5" />
              비활성화
            </button>
          )}

          {/* 삭제(하드) — superadmin 전용, 본인 행에는 노출하지 않음 */}
          {isSuperadmin && !isSelf && (
            <button
              type="button"
              onClick={() => onHardDelete(user)}
              aria-label={`${user.display_name} 삭제`}
              title="삭제 (물리)"
              className="inline-flex items-center justify-center rounded-lg border border-red-200 bg-[var(--bg-surface)] p-1.5 text-red-600 transition-colors hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

function UsersContent() {
  const { data: users, isLoading, error } = useAdminUsers();
  const { data: me } = useMe();
  const deleteUser = useDeleteUser();
  const tT = useTranslations("toast.users");

  const isSuperadmin = me?.system_role === "superadmin";

  // 확인 다이얼로그 대상 (소프트: 비활성화 / 하드: 물리 삭제)
  const [softTarget, setSoftTarget] = useState<UserAdminResponse | null>(null);
  const [hardTarget, setHardTarget] = useState<UserAdminResponse | null>(null);

  const handleDeactivate = () => {
    if (!softTarget) return;
    const name = softTarget.display_name;
    deleteUser.mutate(
      { userId: softTarget.id },
      {
        onSuccess: () => {
          toast.success(tT("deactivateSuccess", { name }));
          setSoftTarget(null);
        },
        onError: (err) => {
          toast.error(err.message || tT("deactivateFail"));
          setSoftTarget(null);
        },
      },
    );
  };

  const handleHardDelete = () => {
    if (!hardTarget) return;
    const name = hardTarget.display_name;
    deleteUser.mutate(
      { userId: hardTarget.id, hard: true },
      {
        onSuccess: () => {
          toast.success(tT("deleteSuccess", { name }));
          setHardTarget(null);
        },
        onError: (err) => {
          toast.error(err.message || tT("deleteFail"));
          setHardTarget(null);
        },
      },
    );
  };

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
          <Users className="h-5 w-5 text-[var(--accent)]" />
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
          <BentoCard className="overflow-hidden p-0">
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
                    관리
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <UserRow
                    key={user.id}
                    user={user}
                    isSelf={user.id === me?.id}
                    isSuperadmin={isSuperadmin}
                    onDeactivate={setSoftTarget}
                    onHardDelete={setHardTarget}
                  />
                ))}
              </tbody>
            </table>
          </BentoCard>

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

      {/* 비활성화(소프트) 확인 다이얼로그 */}
      <ConfirmDialog
        open={softTarget !== null}
        tone="warning"
        title="사용자 비활성화"
        description={
          <>
            <strong className="text-[var(--text-secondary)]">
              {softTarget?.display_name}
            </strong>{" "}
            ({softTarget?.email}) 사용자를 비활성화합니다. 계정은 보존되지만 로그인할 수 없게 됩니다.
          </>
        }
        confirmLabel="비활성화"
        isPending={deleteUser.isPending}
        onConfirm={handleDeactivate}
        onCancel={() => setSoftTarget(null)}
      />

      {/* 삭제(하드) 확인 다이얼로그 — 이메일 재입력 */}
      <ConfirmByTypingDialog
        open={hardTarget !== null}
        title="사용자 영구 삭제"
        description={
          <>
            <strong className="text-[var(--text-secondary)]">
              {hardTarget?.display_name}
            </strong>{" "}
            ({hardTarget?.email}) 사용자를 <strong className="text-red-600">물리적으로 삭제</strong>합니다.
            이 작업은 되돌릴 수 없습니다.
          </>
        }
        confirmPhrase={hardTarget?.email ?? ""}
        confirmLabel="영구 삭제"
        isPending={deleteUser.isPending}
        onConfirm={handleHardDelete}
        onCancel={() => setHardTarget(null)}
      />
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
