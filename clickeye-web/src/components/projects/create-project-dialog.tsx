"use client";

import { useState } from "react";
import { X, AlertCircle, Building2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";

import { useCreateProject } from "@/hooks/use-projects";
import { useMe } from "@/hooks/use-me";
import { useAccessToken } from "@/hooks/use-access-token";
import { controlTower, type ProjectResponse } from "@/lib/api-client";

import { ProjectForm } from "./project-form";

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
  /** 생성 성공 시 호출 — 생성된 프로젝트를 상위로 전달(상세 이동 등). */
  onCreated?: (project: ProjectResponse) => void;
}

export function CreateProjectDialog({ open, onClose, onCreated }: CreateProjectDialogProps) {
  const createProject = useCreateProject();
  const tC = useTranslations("common");
  const tD = useTranslations("common.projectDialog");

  const { data: me } = useMe();
  const token = useAccessToken();

  const isAdmin =
    me?.system_role === "admin" || me?.system_role === "superadmin";

  // 관리자만 대상 고객사를 선택할 수 있다. 일반 사용자는 자신의 조직으로 자동 생성된다.
  const { data: customerList } = useQuery({
    queryKey: ["control-tower", "customers", "org-selector"],
    queryFn: () => controlTower.listCustomers(token, { limit: 200 }),
    enabled: open && isAdmin && !!token,
    staleTime: 5 * 60 * 1000,
  });

  // 사용자가 아직 선택하지 않았으면(null) 자신의 소속 조직을 기본값으로 사용한다.
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const effectiveOrgId = selectedOrgId ?? me?.organization_id ?? "";

  if (!open) return null;

  const showOrgSelector = isAdmin && (customerList?.items.length ?? 0) > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 배경 오버레이 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        role="button"
        tabIndex={0}
        aria-label={tC("aria.close")}
      />

      {/* 다이얼로그 */}
      <div className="relative w-full max-w-md mx-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-2xl shadow-black/10">
        {/* 헤더 */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">{tD("newProject")}</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {createProject.error && (
          <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
            <p className="text-sm text-red-300">{createProject.error.message}</p>
          </div>
        )}

        {/* 대상 조직 셀렉터 (관리자 전용) */}
        {showOrgSelector && (
          <div className="mb-5 space-y-2">
            <label
              htmlFor="organization"
              className="block text-sm font-medium text-[var(--text-secondary)]"
            >
              {tD("orgLabel")}
            </label>
            <div className="relative">
              <Building2 className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
              <select
                id="organization"
                value={effectiveOrgId}
                onChange={(e) => setSelectedOrgId(e.target.value)}
                className="w-full appearance-none rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-3 pl-11 pr-4 text-sm text-[var(--text-primary)] outline-none transition-all focus:border-zinc-400 focus:bg-[var(--bg-hover)] focus:ring-2 focus:ring-zinc-400/20"
              >
                {customerList?.items.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.company_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <ProjectForm
          onSubmit={(data) => {
            createProject.mutate(
              {
                name: data.name,
                description: data.description || undefined,
                // 관리자가 대상 조직을 선택한 경우에만 명시 전달.
                // 일반 사용자는 생략 → 백엔드가 primary organization 사용.
                organization_id: showOrgSelector && effectiveOrgId ? effectiveOrgId : undefined,
              },
              {
                onSuccess: (project) => {
                  onClose();
                  onCreated?.(project);
                },
              },
            );
          }}
          isSubmitting={createProject.isPending}
          submitLabel={tC("actions.create")}
        />

        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 text-center text-sm font-medium text-[var(--text-muted)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
        >
          {tC("actions.cancel")}
        </button>
      </div>
    </div>
  );
}
