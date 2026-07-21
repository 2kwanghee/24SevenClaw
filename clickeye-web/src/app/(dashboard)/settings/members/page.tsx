"use client";

import { Suspense, useState } from "react";
import { UserPlus, Users2, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useForm } from "react-hook-form";

import { RoleGuard } from "@/components/common/role-guard";
import {
  useOrgMembers,
  useAddOrgMember,
  useRemoveOrgMember,
} from "@/hooks/use-rbac";
import { useMe } from "@/hooks/use-me";
import type { OrgMemberResponse, OrgRole } from "@/lib/api-client";

const ORG_ROLE_COLORS: Record<OrgRole, string> = {
  org_admin: "bg-violet-50 text-violet-700 border-violet-200",
  org_member: "bg-blue-50 text-blue-700 border-blue-200",
  org_viewer: "bg-[var(--bg-base)] text-[var(--text-muted)] border-[var(--border-subtle)]",
};

interface InviteFormData {
  email: string;
  userId: string;
  role: OrgRole;
}

function InviteMemberForm({ orgId }: { orgId: string }) {
  const [open, setOpen] = useState(false);
  const addMember = useAddOrgMember(orgId);
  const tT = useTranslations("toast.members");
  const t = useTranslations("settings.members");
  const { register, handleSubmit, reset, setValue, watch } =
    useForm<InviteFormData>({
      defaultValues: { email: "", userId: "", role: "org_member" },
    });

  const selectedRole = watch("role");

  const roleLabels: Record<OrgRole, string> = {
    org_admin: t("roles.org_admin"),
    org_member: t("roles.org_member"),
    org_viewer: t("roles.org_viewer"),
  };

  const onSubmit = (data: InviteFormData) => {
    if (!data.userId.trim()) {
      toast.error(tT("userIdRequired"));
      return;
    }

    addMember.mutate(
      { user_id: data.userId, org_role: data.role },
      {
        onSuccess: () => {
          toast.success(tT("addSuccess"));
          reset();
          setOpen(false);
        },
        onError: (err) => {
          toast.error(err.message || tT("addFail"));
        },
      },
    );
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-fg)] transition-all hover:opacity-90"
      >
        <UserPlus className="h-4 w-4" />
        {t("inviteBtn")}
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex flex-col gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 sm:flex-row sm:items-end"
    >
      <div className="flex-1">
        <label
          htmlFor="userId"
          className="mb-1 block text-xs font-medium text-[var(--text-muted)]"
        >
          {t("userIdLabel")}
        </label>
        <input
          id="userId"
          type="text"
          placeholder={t("userIdPlaceholder")}
          {...register("userId")}
          className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)]"
        />
      </div>

      <div className="w-40">
        <label
          htmlFor="role"
          className="mb-1 block text-xs font-medium text-[var(--text-muted)]"
        >
          {t("roleLabel")}
        </label>
        <select
          id="role"
          value={selectedRole}
          onChange={(e) => setValue("role", e.target.value as OrgRole)}
          className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none transition-colors focus:border-[var(--accent)]"
        >
          {(Object.entries(roleLabels) as [OrgRole, string][]).map(
            ([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ),
          )}
        </select>
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={addMember.isPending}
          className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90 disabled:opacity-50"
        >
          {addMember.isPending ? t("addingBtn") : t("addBtn")}
        </button>
        <button
          type="button"
          onClick={() => {
            reset();
            setOpen(false);
          }}
          className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
        >
          {t("cancelBtn")}
        </button>
      </div>
    </form>
  );
}

function MemberRow({
  member,
  orgId,
}: {
  member: OrgMemberResponse;
  orgId: string;
}) {
  const removeMember = useRemoveOrgMember(orgId);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const tT = useTranslations("toast.members");
  const t = useTranslations("settings.members");
  const roleLabels: Record<OrgRole, string> = {
    org_admin: t("roles.org_admin"),
    org_member: t("roles.org_member"),
    org_viewer: t("roles.org_viewer"),
  };

  const handleRemove = () => {
    removeMember.mutate(member.user_id, {
      onSuccess: () => {
        toast.success(tT("removeSuccess"));
        setConfirmDelete(false);
      },
      onError: (err) => {
        toast.error(err.message || tT("removeFail"));
        setConfirmDelete(false);
      },
    });
  };

  const role = member.org_role as OrgRole;

  return (
    <tr className="border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-hover)]">
      <td className="px-4 py-3">
        <code className="rounded bg-[var(--bg-base)] px-1.5 py-0.5 text-xs text-[var(--text-secondary)]">
          {member.user_id.slice(0, 8)}...
        </code>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-xs font-medium ${ORG_ROLE_COLORS[role]}`}
        >
          {roleLabels[role]}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            member.is_active
              ? "bg-emerald-50 text-emerald-700"
              : "bg-[var(--bg-base)] text-[var(--text-muted)]"
          }`}
        >
          {member.is_active ? t("statusActive") : t("statusInactive")}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
        {new Date(member.joined_at).toLocaleDateString("ko-KR")}
      </td>
      <td className="px-4 py-3 text-right">
        {confirmDelete ? (
          <div className="inline-flex items-center gap-2">
            <span className="text-xs text-red-700">{t("deleteConfirm")}</span>
            <button
              type="button"
              onClick={handleRemove}
              disabled={removeMember.isPending}
              className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-500 disabled:opacity-50"
            >
              {t("confirmBtn")}
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(false)}
              className="rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              {t("cancelBtn")}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-red-50 hover:text-red-700"
            title={t("removeTitle")}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </td>
    </tr>
  );
}

function MembersContent() {
  const { data: me, isLoading: meLoading } = useMe();
  const orgId = me?.organization_id ?? "";
  const { data: members, isLoading, error } = useOrgMembers(orgId);
  const t = useTranslations("settings.members");

  // 소속 조직이 없는 사용자 처리
  if (!meLoading && !orgId) {
    return (
      <div>
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
            <Users2 className="h-5 w-5 text-[var(--text-secondary)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <Users2 className="h-12 w-12 text-[var(--text-muted)]" />
          <p className="text-sm text-[var(--text-muted)]">{t("noOrg")}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
            <Users2 className="h-5 w-5 text-[var(--text-secondary)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
          </div>
        </div>
        {orgId && <InviteMemberForm orgId={orgId} />}
      </div>

      {/* 로딩 */}
      {(meLoading || isLoading) && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-xl bg-[var(--bg-hover)]"
            />
          ))}
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {t("loadError")}
        </div>
      )}

      {/* 테이블 */}
      {members && members.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  {t("colUser")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  {t("colRole")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  {t("colStatus")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  {t("colJoinedAt")}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  {t("colActions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <MemberRow key={member.id} member={member} orgId={orgId} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 빈 상태 */}
      {members && members.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <Users2 className="h-12 w-12 text-[var(--text-muted)]" />
          <div>
            <p className="text-sm text-[var(--text-muted)]">{t("emptyState")}</p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">{t("emptyStateHint")}</p>
          </div>
        </div>
      )}

      {/* 멤버 수 */}
      {members && members.length > 0 && (
        <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
          {t("totalCount", { count: members.length })}
        </p>
      )}
    </div>
  );
}

export default function SettingsMembersPage() {
  return (
    <RoleGuard permissions={["org:manage"]}>
      <Suspense
        fallback={
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-14 animate-pulse rounded-xl bg-[var(--bg-hover)]"
              />
            ))}
          </div>
        }
      >
        <MembersContent />
      </Suspense>
    </RoleGuard>
  );
}
