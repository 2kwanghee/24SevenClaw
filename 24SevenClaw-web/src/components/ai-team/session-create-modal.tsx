"use client";

import { useState } from "react";
import { X, Loader2, Sparkles, Check } from "lucide-react";

import { useCreateSession, useDecompose, useAssign } from "@/hooks/use-orchestrator";
import type { SubTaskResponse, SubTaskRole } from "@/lib/api-client";

type ModalStep = "form" | "decomposing" | "review" | "assigning" | "done";

interface SessionCreateModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onCreated: (sessionId: string) => void;
}

export function SessionCreateModal({
  projectId,
  isOpen,
  onClose,
  onCreated,
}: SessionCreateModalProps) {
  const [step, setStep] = useState<ModalStep>("form");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [subtasks, setSubtasks] = useState<SubTaskResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  const create = useCreateSession(projectId);
  const decompose = useDecompose();
  const assign = useAssign();

  const reset = () => {
    setStep("form");
    setTitle("");
    setDescription("");
    setSessionId("");
    setSubtasks([]);
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleCreate = async () => {
    if (!title.trim()) return;
    setError(null);

    try {
      // 1. 세션 생성
      const session = await create.mutateAsync({
        title: title.trim(),
        description: description.trim() || undefined,
      });
      setSessionId(session.id);

      // 2. Decompose
      setStep("decomposing");
      const decomposeResult = await decompose.mutateAsync({
        sessionId: session.id,
      });
      setSubtasks(decomposeResult.subtasks);
      setStep("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "세션 생성에 실패했습니다");
      setStep("form");
    }
  };

  const handleAssign = async () => {
    setStep("assigning");
    setError(null);
    try {
      const result = await assign.mutateAsync({ sessionId });
      setSubtasks(result.subtasks);
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "배정에 실패했습니다");
      setStep("review");
    }
  };

  const handleDone = () => {
    onCreated(sessionId);
    handleClose();
  };

  if (!isOpen) return null;

  const ROLE_LABELS: Record<SubTaskRole, string> = {
    architect: "아키텍트",
    frontend: "프론트엔드",
    backend: "백엔드",
    qa: "QA",
    security: "보안",
    devops: "DevOps",
    reviewer: "리뷰어",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="새 작업 요청"
    >
      <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl">
        {/* 닫기 */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute right-4 top-4 rounded-lg p-1 text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
          aria-label="닫기"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Step: 폼 입력 */}
        {step === "form" && (
          <>
            <h2 className="mb-4 text-lg font-semibold text-white">
              새 작업 요청
            </h2>

            {error && (
              <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label htmlFor="session-title" className="mb-1.5 block text-xs font-medium text-slate-400">
                  작업 제목 *
                </label>
                <input
                  id="session-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="구현할 기능을 설명하세요..."
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-violet-500/30 focus:outline-none"
                />
              </div>
              <div>
                <label htmlFor="session-desc" className="mb-1.5 block text-xs font-medium text-slate-400">
                  상세 설명
                </label>
                <textarea
                  id="session-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  placeholder="작업의 배경, 요구사항, 제약조건 등..."
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-violet-500/30 focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleClose}
                className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 transition-colors hover:bg-white/5"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={!title.trim() || create.isPending}
                className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
              >
                {create.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                생성 & 분해
              </button>
            </div>
          </>
        )}

        {/* Step: Decomposing */}
        {step === "decomposing" && (
          <div className="flex flex-col items-center gap-3 py-10">
            <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
            <p className="text-sm text-slate-300">작업을 분해하는 중...</p>
            <p className="text-xs text-slate-500">
              AI가 서브태스크를 생성하고 있습니다
            </p>
          </div>
        )}

        {/* Step: Review subtasks */}
        {step === "review" && (
          <>
            <h2 className="mb-1 text-lg font-semibold text-white">
              서브태스크 확인
            </h2>
            <p className="mb-4 text-xs text-slate-500">
              {subtasks.length}개의 태스크가 생성되었습니다. 배정을 확정하세요.
            </p>

            {error && (
              <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                {error}
              </div>
            )}

            <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
              {subtasks.map((st) => (
                <div
                  key={st.id}
                  className="flex items-start gap-3 rounded-lg border border-white/5 bg-white/[0.02] p-3"
                >
                  <span className="mt-0.5 shrink-0 rounded bg-violet-500/10 px-1.5 py-0.5 text-[10px] font-medium text-violet-400">
                    {ROLE_LABELS[st.assigned_role] ?? st.assigned_role}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200">{st.title}</p>
                    {st.description && (
                      <p className="mt-0.5 text-xs text-slate-500 line-clamp-1">
                        {st.description}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleClose}
                className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 transition-colors hover:bg-white/5"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleAssign}
                disabled={assign.isPending}
                className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
              >
                {assign.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                배정 확정
              </button>
            </div>
          </>
        )}

        {/* Step: Assigning */}
        {step === "assigning" && (
          <div className="flex flex-col items-center gap-3 py-10">
            <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
            <p className="text-sm text-slate-300">AI 팀을 배정하는 중...</p>
          </div>
        )}

        {/* Step: Done */}
        {step === "done" && (
          <>
            <div className="flex flex-col items-center gap-3 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10">
                <Check className="h-6 w-6 text-emerald-400" />
              </div>
              <p className="text-sm font-medium text-white">
                작업이 생성되었습니다!
              </p>
              <p className="text-xs text-slate-500">
                {subtasks.length}개 서브태스크가 배정되었습니다
              </p>
            </div>
            <div className="flex justify-center">
              <button
                type="button"
                onClick={handleDone}
                className="rounded-lg bg-violet-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500"
              >
                대시보드로 이동
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
