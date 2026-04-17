"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { RoleGuard } from "@/components/common/role-guard";
import {
  pmProfiles,
  type PMCompositionResponse,
  type PMCompositionCreateRequest,
} from "@/lib/api-client";

const COMPONENT_TYPES = ["agent", "skill", "hook", "mcp_server", "plugin"];

function CompositionPage({ profileId }: { profileId: string }) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const qc = useQueryClient();

  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState<PMCompositionCreateRequest>({
    component_type: "agent",
    component_slug: "",
    component_name: "",
    config: {},
    display_order: 0,
    is_required: false,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["pm-composition", profileId],
    queryFn: () => pmProfiles.getComposition(token, profileId),
    enabled: !!token,
  });

  const { data: profile } = useQuery({
    queryKey: ["pm-profile-detail", profileId],
    queryFn: () => pmProfiles.get(token, profileId),
    enabled: !!token,
  });

  const createMutation = useMutation({
    mutationFn: (req: PMCompositionCreateRequest) =>
      pmProfiles.createComposition(token, profileId, req),
    onSuccess: () => {
      toast.success("구성 컴포넌트가 추가되었습니다.");
      qc.invalidateQueries({ queryKey: ["pm-composition", profileId] });
      setShowAdd(false);
      setAddForm({
        component_type: "agent", component_slug: "", component_name: "",
        config: {}, display_order: 0, is_required: false,
      });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (compositionId: string) =>
      pmProfiles.deleteComposition(token, profileId, compositionId),
    onSuccess: () => {
      toast.success("구성 컴포넌트가 삭제되었습니다.");
      qc.invalidateQueries({ queryKey: ["pm-composition", profileId] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const allItems: PMCompositionResponse[] = data
    ? [
        ...data.agents,
        ...data.skills,
        ...data.hooks,
        ...data.mcp_servers,
        ...data.plugins,
      ].sort((a, b) => a.display_order - b.display_order)
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href={`/admin/pm/${profileId}`}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {profile?.name ?? "PM 편집"}
          </Link>
          <span className="text-slate-700">/</span>
          <h1 className="text-sm font-semibold text-white">구성 관리</h1>
        </div>
        <button
          type="button"
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500"
        >
          <Plus className="h-4 w-4" />
          컴포넌트 추가
        </button>
      </div>

      {showAdd && (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">구성 컴포넌트 추가</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">타입</label>
              <select
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                value={addForm.component_type}
                onChange={(e) => setAddForm({ ...addForm, component_type: e.target.value })}
              >
                {COMPONENT_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Slug</label>
              <input
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                placeholder="예: code-reviewer"
                value={addForm.component_slug}
                onChange={(e) => setAddForm({ ...addForm, component_slug: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">이름</label>
              <input
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                placeholder="예: 코드 리뷰어"
                value={addForm.component_name}
                onChange={(e) => setAddForm({ ...addForm, component_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">표시 순서</label>
              <input
                type="number"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                min={0}
                value={addForm.display_order ?? 0}
                onChange={(e) => setAddForm({ ...addForm, display_order: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="is_required"
              type="checkbox"
              checked={addForm.is_required ?? false}
              onChange={(e) => setAddForm({ ...addForm, is_required: e.target.checked })}
              className="h-4 w-4 rounded border-white/20"
            />
            <label htmlFor="is_required" className="text-sm text-slate-300">필수 컴포넌트</label>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => createMutation.mutate(addForm)}
              disabled={createMutation.isPending || !addForm.component_slug || !addForm.component_name}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
            >
              {createMutation.isPending ? "추가 중..." : "추가"}
            </button>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 transition-colors hover:bg-white/5"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {isLoading && <div className="py-12 text-center text-sm text-slate-500">불러오는 중...</div>}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {(error as Error).message}
        </div>
      )}

      {allItems.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-white/10">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">순서</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">타입</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Slug</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">이름</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">필수</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-400">액션</th>
              </tr>
            </thead>
            <tbody>
              {allItems.map((item) => (
                <tr key={item.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-4 py-3 text-sm text-slate-400">{item.display_order}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-slate-300">
                      {item.component_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300 font-mono">{item.component_slug}</td>
                  <td className="px-4 py-3 text-sm text-white">{item.component_name}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{item.is_required ? "✓" : "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => {
                        if (!confirm(`"${item.component_name}" 컴포넌트를 삭제하시겠습니까?`)) return;
                        deleteMutation.mutate(item.id);
                      }}
                      disabled={deleteMutation.isPending}
                      className="inline-flex items-center gap-1 rounded-lg border border-red-500/20 px-2.5 py-1 text-xs text-red-400 transition-colors hover:bg-red-500/10 disabled:opacity-50"
                    >
                      <Trash2 className="h-3 w-3" />
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isLoading && allItems.length === 0 && (
        <div className="py-12 text-center text-sm text-slate-600">
          구성 컴포넌트가 없습니다. 위 버튼으로 추가하세요.
        </div>
      )}
    </div>
  );
}

export default function AdminPMCompositionPage() {
  const params = useParams<{ id: string }>();
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <CompositionPage profileId={params.id} />
    </RoleGuard>
  );
}
