"use client";

import { X, AlertCircle } from "lucide-react";
import { useCreateProject } from "@/hooks/use-projects";

import { ProjectForm } from "./project-form";

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
}

export function CreateProjectDialog({ open, onClose }: CreateProjectDialogProps) {
  const createProject = useCreateProject();

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
        aria-label="닫기"
      />

      {/* 다이얼로그 */}
      <div className="relative w-full max-w-md mx-4 rounded-2xl border border-white/10 bg-slate-900 p-8 shadow-2xl shadow-black/50">
        {/* 헤더 */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">새 프로젝트</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
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
          submitLabel="생성"
        />

        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-xl border border-white/5 bg-white/[0.02] py-2.5 text-center text-sm font-medium text-slate-400 transition-all hover:bg-white/5 hover:text-slate-300"
        >
          취소
        </button>
      </div>
    </div>
  );
}
