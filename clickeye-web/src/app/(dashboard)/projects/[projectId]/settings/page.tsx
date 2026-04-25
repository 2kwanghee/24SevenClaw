"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Archive,
  RotateCcw,
} from "lucide-react";

import { ProjectForm } from "@/components/projects/project-form";
import { useProject, useUpdateProject } from "@/hooks/use-projects";
import { ApiClientError } from "@/lib/api-client";

export default function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const { data: project, isLoading, error: loadError } = useProject(projectId);
  const updateProject = useUpdateProject(projectId);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
        <p className="mt-4 text-sm text-[var(--text-muted)]">불러오는 중...</p>
      </div>
    );
  }

  if (loadError || !project) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">프로젝트를 찾을 수 없습니다.</p>
        <Link
          href="/projects"
          className="mt-3 inline-block text-sm text-zinc-500 transition-colors hover:text-zinc-900 hover:underline"
        >
          목록으로 돌아가기
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {project.name}
        </Link>
        <h1 className="mt-3 text-2xl font-bold text-[var(--text-primary)]">프로젝트 설정</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          프로젝트 정보를 수정하고 상태를 관리하세요
        </p>
      </div>

      {/* 기본 정보 */}
      <div className="mx-auto max-w-lg space-y-6">
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <h2 className="mb-6 text-lg font-semibold text-[var(--text-primary)]">기본 정보</h2>

          {error && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
          {success && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
              <p className="text-sm text-emerald-700">프로젝트가 업데이트되었습니다.</p>
            </div>
          )}

          <ProjectForm
            defaultValues={{
              name: project.name,
              description: project.description ?? "",
            }}
            isSubmitting={updateProject.isPending}
            submitLabel="저장"
            onSubmit={(data) => {
              setError(null);
              setSuccess(false);
              updateProject.mutate(
                { name: data.name, description: data.description || undefined },
                {
                  onSuccess: () => {
                    setSuccess(true);
                    router.refresh();
                  },
                  onError: (err) => {
                    if (err instanceof ApiClientError) {
                      setError(err.detail);
                    } else {
                      setError("업데이트에 실패했습니다.");
                    }
                  },
                },
              );
            }}
          />
        </div>

        {/* 상태 변경 */}
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">프로젝트 상태</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            프로젝트를 보관하거나 다시 활성화할 수 있습니다
          </p>

          <div className="mt-6">
            {project.status === "active" ? (
              <button
                type="button"
                onClick={() =>
                  updateProject.mutate(
                    { status: "archived" },
                    { onSuccess: () => router.refresh() },
                  )
                }
                disabled={updateProject.isPending}
                className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-5 py-2.5 text-sm font-medium text-amber-700 transition-all hover:bg-amber-100 disabled:opacity-50"
              >
                <Archive className="h-4 w-4" />
                보관 처리
              </button>
            ) : (
              <button
                type="button"
                onClick={() =>
                  updateProject.mutate(
                    { status: "active" },
                    { onSuccess: () => router.refresh() },
                  )
                }
                disabled={updateProject.isPending}
                className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-5 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] disabled:opacity-50"
              >
                <RotateCcw className="h-4 w-4" />
                활성화
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
