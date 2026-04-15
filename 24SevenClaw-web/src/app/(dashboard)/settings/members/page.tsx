"use client";

import { Suspense, useState } from "react";
import { UserPlus, Users2, Trash2, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { useForm } from "react-hook-form";

import { RoleGuard } from "@/components/common/role-guard";
import {
  useOrgMembers,
  useAddOrgMember,
  useRemoveOrgMember,
} from "@/hooks/use-rbac";
import type { OrgMemberResponse, OrgRole } from "@/lib/api-client";

// TODO: 실제 조직 ID는 세션 또는 URL에서 가져와야 함
const DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001";

const ORG_ROLE_LABELS: Record<OrgRole, string> = {
  org_admin: "관리자",
  org_member: "멤버",
  org_viewer: "뷰어",
};

const ORG_ROLE_COLORS: Record<OrgRole, string> = {
  org_admin: "bg-violet-500/10 text-violet-300 border-violet-500/20",
  org_member: "bg-blue-500/10 text-blue-300 border-blue-500/20",
  org_viewer: "bg-slate-500/10 text-slate-300 border-slate-500/20",
};

interface InviteFormData {
  email: string;
  userId: string;
  role: OrgRole;
}

function InviteMemberForm({ orgId }: { orgId: string }) {
  const [open, setOpen] = useState(false);
  const addMember = useAddOrgMember(orgId);
  const { register, handleSubmit, reset, setValue, watch } =
    useForm<InviteFormData>({
      defaultValues: { email: "", userId: "", role: "org_member" },
    });

  const selectedRole = watch("role");

  const onSubmit = (data: InviteFormData) => {
    if (!data.userId.trim()) {
      toast.error("사용자 ID를 입력하세요");
      return;
    }

    addMember.mutate(
      { user_id: data.userId, org_role: data.role },
      {
        onSuccess: () => {
          toast.success("멤버가 추가되었습니다");
          reset();
          setOpen(false);
        },
        onError: (err) => {
          toast.error(err.message || "멤버 추가에 실패했습니다");
        },
      },
    );
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-violet-600/25 transition-all hover:bg-violet-500 hover:shadow-violet-500/30"
      >
        <UserPlus className="h-4 w-4" />
        멤버 초대
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4 sm:flex-row sm:items-end"
    >
      <div className="flex-1">
        <label
          htmlFor="userId"
          className="mb-1 block text-xs font-medium text-slate-400"
        >
          사용자 ID
        </label>
        <input
          id="userId"
          type="text"
          placeholder="UUID 입력..."
          {...register("userId")}
          className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white placeholder-slate-500 outline-none transition-colors focus:border-violet-500/50"
        />
      </div>

      <div className="w-40">
        <label
          htmlFor="role"
          className="mb-1 block text-xs font-medium text-slate-400"
        >
          역할
        </label>
        <select
          id="role"
          value={selectedRole}
          onChange={(e) => setValue("role", e.target.value as OrgRole)}
          className="w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white outline-none transition-colors focus:border-violet-500/50"
        >
          {(Object.entries(ORG_ROLE_LABELS) as [OrgRole, string][]).map(
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
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
        >
          {addMember.isPending ? "추가 중..." : "추가"}
        </button>
        <button
          type="button"
          onClick={() => {
            reset();
            setOpen(false);
          }}
          className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
        >
          취소
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

  const handleRemove = () => {
    removeMember.mutate(member.user_id, {
      onSuccess: () => {
        toast.success("멤버가 제거되었습니다");
        setConfirmDelete(false);
      },
      onError: (err) => {
        toast.error(err.message || "멤버 제거에 실패했습니다");
        setConfirmDelete(false);
      },
    });
  };

  const role = member.org_role as OrgRole;

  return (
    <tr className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
      <td className="px-4 py-3">
        <code className="rounded bg-white/[0.05] px-1.5 py-0.5 text-xs text-slate-300">
          {member.user_id.slice(0, 8)}...
        </code>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-xs font-medium ${ORG_ROLE_COLORS[role]}`}
        >
          {ORG_ROLE_LABELS[role]}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            member.is_active
              ? "bg-emerald-500/10 text-emerald-300"
              : "bg-slate-500/10 text-slate-400"
          }`}
        >
          {member.is_active ? "활성" : "비활성"}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {new Date(member.joined_at).toLocaleDateString("ko-KR")}
      </td>
      <td className="px-4 py-3 text-right">
        {confirmDelete ? (
          <div className="inline-flex items-center gap-2">
            <span className="text-xs text-red-400">삭제하시겠습니까?</span>
            <button
              type="button"
              onClick={handleRemove}
              disabled={removeMember.isPending}
              className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-500 disabled:opacity-50"
            >
              확인
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(false)}
              className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 transition-colors hover:bg-white/5"
            >
              취소
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-red-500/10 hover:text-red-400"
            title="멤버 제거"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </td>
    </tr>
  );
}

function MembersContent() {
  const orgId = DEFAULT_ORG_ID;
  const { data: members, isLoading, error } = useOrgMembers(orgId);

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10">
            <Users2 className="h-5 w-5 text-violet-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">조직 멤버</h1>
            <p className="mt-0.5 text-sm text-slate-400">
              조직 멤버를 초대하고 관리합니다
            </p>
          </div>
        </div>
        <InviteMemberForm orgId={orgId} />
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-xl bg-white/[0.03]"
            />
          ))}
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">
          멤버 목록을 불러오지 못했습니다.
        </div>
      )}

      {/* 테이블 */}
      {members && members.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-white/5 bg-white/[0.02]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.03]">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  사용자
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  역할
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  상태
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  가입일
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">
                  관리
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
          <Users2 className="h-12 w-12 text-slate-600" />
          <div>
            <p className="text-sm text-slate-400">조직 멤버가 없습니다</p>
            <p className="mt-1 text-xs text-slate-600">
              위의 &quot;멤버 초대&quot; 버튼으로 멤버를 추가하세요
            </p>
          </div>
        </div>
      )}

      {/* 멤버 수 */}
      {members && members.length > 0 && (
        <p className="mt-4 text-center text-xs text-slate-600">
          총 {members.length}명
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
                className="h-14 animate-pulse rounded-xl bg-white/[0.03]"
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
