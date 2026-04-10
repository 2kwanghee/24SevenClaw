"use client";

import { AlertTriangle } from "lucide-react";

interface DeleteProjectDialogProps {
  projectName: string;
  isOpen: boolean;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteProjectDialog({
  projectName,
  isOpen,
  isDeleting,
  onConfirm,
  onCancel,
}: DeleteProjectDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 배경 오버레이 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
        onKeyDown={(e) => e.key === "Escape" && onCancel()}
        role="button"
        tabIndex={0}
        aria-label="닫기"
      />

      {/* 다이얼로그 */}
      <div className="relative w-full max-w-sm mx-4 rounded-2xl border border-white/10 bg-slate-900 p-8 shadow-2xl shadow-black/50">
        {/* 아이콘 */}
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10">
          <AlertTriangle className="h-6 w-6 text-red-400" />
        </div>

        <h3 className="mt-4 text-lg font-semibold text-white">프로젝트 삭제</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">
          <strong className="text-slate-200">{projectName}</strong> 프로젝트를 삭제하시겠습니까?
          이 작업은 되돌릴 수 없습니다.
        </p>

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl border border-white/10 bg-white/5 py-2.5 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
          >
            취소
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex-1 rounded-xl bg-red-600 py-2.5 text-sm font-medium text-white shadow-lg shadow-red-600/25 transition-all hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? "삭제 중..." : "삭제"}
          </button>
        </div>
      </div>
    </div>
  );
}
