"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { Plus, Users, Pencil, Trash2, AlertCircle, CheckCircle2, XCircle, Heart, Frown } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { RoleGuard } from "@/components/common/role-guard";
import { BentoCard } from "@/components/ui/bento";
import {
  pmProfiles,
  type PMProfileWithMetrics,
  type PMProfileCreateRequest,
} from "@/lib/api-client";

function PMListPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const qc = useQueryClient();
  const tT = useTranslations("toast.pm");

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<PMProfileCreateRequest>({
    name: "",
    slug: "",
    title: "",
    domain: "",
    description: "",
    bio_long: "",
    is_active: true,
    specialties: [],
    tech_stack_tags: [],
    industry_tags: [],
    preferred_solution_types: [],
    language: "ko",
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-pm-profiles"],
    queryFn: async () => {
      const list = await pmProfiles.list(token, { limit: 100 });
      const withMetrics = await Promise.all(
        list.items.map((p) => pmProfiles.get(token, p.id)),
      );
      return { items: withMetrics, total: list.total };
    },
    enabled: !!token,
  });

  const createMutation = useMutation({
    mutationFn: (req: PMProfileCreateRequest) => pmProfiles.create(token, req),
    onSuccess: () => {
      toast.success(tT("createSuccess"));
      qc.invalidateQueries({ queryKey: ["admin-pm-profiles"] });
      setShowCreate(false);
      setCreateForm({
        name: "", slug: "", title: "", domain: "", description: "",
        bio_long: "", is_active: true, specialties: [], tech_stack_tags: [],
        industry_tags: [], preferred_solution_types: [], language: "ko",
      });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => pmProfiles.delete(token, id),
    onSuccess: () => {
      toast.success(tT("deleteSuccess"));
      qc.invalidateQueries({ queryKey: ["admin-pm-profiles"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleCreate = () => {
    if (!createForm.name || !createForm.slug) {
      toast.error(tT("nameSlugRequired"));
      return;
    }
    createMutation.mutate(createForm);
  };

  const handleDelete = (pm: PMProfileWithMetrics) => {
    if (!confirm(`"${pm.name}" PM을 삭제하시겠습니까?`)) return;
    deleteMutation.mutate(pm.id);
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
            <Users className="h-5 w-5 text-[var(--text-secondary)]" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[var(--text-primary)]">PM 프로필 관리</h1>
            <p className="text-xs text-[var(--text-muted)]">AI PM 프로필 생성 및 편집 (관리자 전용)</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90"
        >
          <Plus className="h-4 w-4" />
          PM 생성
        </button>
      </div>

      {/* 생성 다이얼로그 */}
      {showCreate && (
        <BentoCard className="space-y-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">새 PM 프로필 생성</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-[var(--text-muted)] mb-1">이름 *</label>
              <input
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder="예: Alex Chen"
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--text-muted)] mb-1">Slug *</label>
              <input
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder="예: alex-chen"
                value={createForm.slug}
                onChange={(e) => setCreateForm({ ...createForm, slug: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--text-muted)] mb-1">직함</label>
              <input
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder="예: Senior PM"
                value={createForm.title ?? ""}
                onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--text-muted)] mb-1">도메인</label>
              <input
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder="예: saas, fintech"
                value={createForm.domain ?? ""}
                onChange={(e) => setCreateForm({ ...createForm, domain: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1">한 줄 설명</label>
            <input
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
              placeholder="PM에 대한 간략한 설명"
              value={createForm.description ?? ""}
              onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
            />
          </div>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={handleCreate}
              disabled={createMutation.isPending}
              className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90 disabled:opacity-50"
            >
              {createMutation.isPending ? "생성 중..." : "생성"}
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              취소
            </button>
          </div>
        </BentoCard>
      )}

      {/* 로딩/에러 */}
      {isLoading && (
        <div className="py-12 text-center text-sm text-[var(--text-muted)]">불러오는 중...</div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {(error as Error).message}
        </div>
      )}

      {/* PM 목록 */}
      {data && (
        <BentoCard className="block overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">이름</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">도메인</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">전문분야</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">사용횟수</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">피드백</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">상태</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">액션</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((pm) => (
                <tr key={pm.id} className="border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-hover)]">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-[var(--text-primary)]">{pm.name}</p>
                    <p className="text-xs text-[var(--text-muted)]">{pm.slug}</p>
                    {pm.title && <p className="text-xs text-[var(--text-muted)]">{pm.title}</p>}
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">{pm.domain ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {pm.specialties.slice(0, 3).map((s) => (
                        <span
                          key={s}
                          className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-0.5 text-[10px] text-[var(--text-muted)]"
                        >
                          {s}
                        </span>
                      ))}
                      {pm.specialties.length > 3 && (
                        <span className="text-[10px] text-[var(--text-muted)]">+{pm.specialties.length - 3}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm font-medium text-[var(--text-secondary)]">
                      {pm.usage_count}
                    </span>
                    <span className="ml-1 text-[10px] text-[var(--text-muted)]">회</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 text-xs text-rose-700">
                        <Heart className="h-3 w-3 fill-rose-500 text-rose-500" aria-hidden="true" />
                        {pm.like_count}
                      </span>
                      <span className="flex items-center gap-1 text-xs text-sky-700">
                        <Frown className="h-3 w-3" aria-hidden="true" />
                        {pm.dislike_count}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {pm.is_active ? (
                      <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
                        <CheckCircle2 className="h-3 w-3" /> 활성
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-[var(--text-muted)]">
                        <XCircle className="h-3 w-3" /> 비활성
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        href={`/admin/pm/${pm.id}`}
                        className="flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2.5 py-1 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                      >
                        <Pencil className="h-3 w-3" />
                        편집
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleDelete(pm)}
                        disabled={deleteMutation.isPending}
                        className="flex items-center gap-1 rounded-lg border border-red-200 px-2.5 py-1 text-xs text-red-700 transition-colors hover:bg-red-50 disabled:opacity-50"
                      >
                        <Trash2 className="h-3 w-3" />
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-[var(--text-muted)]">
                    PM 프로필이 없습니다. 위 버튼으로 추가하세요.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </BentoCard>
      )}
    </div>
  );
}

export default function AdminPMPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <PMListPage />
    </RoleGuard>
  );
}
