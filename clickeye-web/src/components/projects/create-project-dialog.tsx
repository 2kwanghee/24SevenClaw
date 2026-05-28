"use client";

import { X, AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCreateProject } from "@/hooks/use-projects";

import { ProjectForm } from "./project-form";

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
}

export function CreateProjectDialog({ open, onClose }: CreateProjectDialogProps) {
  const createProject = useCreateProject();
  const tC = useTranslations("common");
  const tD = useTranslations("common.projectDialog");

  if (!open) return null;

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

        <ProjectForm
          onSubmit={(data) => {
            createProject.mutate(
              { name: data.name, description: data.description || undefined },
              { onSuccess: onClose },
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
