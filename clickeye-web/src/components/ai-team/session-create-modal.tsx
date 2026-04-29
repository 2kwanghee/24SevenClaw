"use client";

import { useState } from "react";
import { X, Loader2, Sparkles, Check, Link2, AlertTriangle } from "lucide-react";
import Link from "next/link";

import { useCreateSession, useDecompose, useAssign, useGenerateDrafts, usePushToLinear } from "@/hooks/use-orchestrator";
import type { SubTaskResponse, SubTaskRole, PushToLinearResponse } from "@/lib/api-client";

type ModalStep = "form" | "decomposing" | "review" | "assigning" | "drafting" | "pushing" | "done";

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
  const [linearResult, setLinearResult] = useState<PushToLinearResponse | null>(null);
  const [linearError, setLinearError] = useState<string | null>(null);

  const create = useCreateSession(projectId);
  const decompose = useDecompose();
  const assign = useAssign();
  const generateDrafts = useGenerateDrafts();
  const pushToLinear = usePushToLinear();

  const reset = () => {
    setStep("form");
    setTitle("");
    setDescription("");
    setSessionId("");
    setSubtasks([]);
    setError(null);
    setLinearResult(null);
    setLinearError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleCreate = async () => {
    if (!title.trim()) return;
    setError(null);

    try {
      const session = await create.mutateAsync({
        title: title.trim(),
        description: description.trim() || undefined,
      });
      setSessionId(session.id);

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

      // 초안 생성 → 자동 파이프라인 시작 (drafting → reviewing → integrating → validating)
      setStep("drafting");
      await generateDrafts.mutateAsync({ sessionId });

      // Linear 이슈 등록
      setStep("pushing");
      try {
        const pushed = await pushToLinear.mutateAsync({ sessionId });
        setLinearResult(pushed);
      } catch (pushErr) {
        const msg = pushErr instanceof Error ? pushErr.message : "Linear 이슈 생성 실패";
        setLinearError(msg);
      }

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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="새 작업 요청"
    >
      <div className="relative w-full max-w-lg rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-2xl">
        {/* 닫기 */}
        <button
          type="button"
          onClick={handleClose}
          className="absolute right-4 top-4 rounded-lg p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          aria-label="닫기"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Step: 폼 입력 */}
        {step === "form" && (
          <>
            <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
              새 작업 요청
            </h2>

            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {error}
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label htmlFor="session-title" className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                  작업 제목 *
                </label>
                <input
                  id="session-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="구현할 기능을 설명하세요..."
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-zinc-400 focus:outline-none"
                />
              </div>
              <div>
                <label htmlFor="session-desc" className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
                  상세 설명
                </label>
                <textarea data-gramm="false" data-gramm_editor="false"
                  id="session-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  placeholder="작업의 배경, 요구사항, 제약조건 등..."
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-zinc-400 focus:outline-none"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleClose}
                className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleCreate}
                disabled={!title.trim() || create.isPending}
                className="flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
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
            <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
            <p className="text-sm text-[var(--text-secondary)]">작업을 분해하는 중...</p>
            <p className="text-xs text-[var(--text-muted)]">
              AI가 서브태스크를 생성하고 있습니다
            </p>
          </div>
        )}

        {/* Step: Review subtasks */}
        {step === "review" && (
          <>
            <h2 className="mb-1 text-lg font-semibold text-[var(--text-primary)]">
              서브태스크 확인
            </h2>
            <p className="mb-4 text-xs text-[var(--text-muted)]">
              {subtasks.length}개의 태스크가 생성되었습니다. 배정을 확정하면 Linear 이슈가 자동 등록됩니다.
            </p>

            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {error}
              </div>
            )}

            <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
              {subtasks.map((st) => (
                <div
                  key={st.id}
                  className="flex items-start gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-3"
                >
                  <span className="mt-0.5 shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-medium text-zinc-700">
                    {ROLE_LABELS[st.assigned_role] ?? st.assigned_role}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--text-primary)]">{st.title}</p>
                    {st.description && (
                      <p className="mt-0.5 text-xs text-[var(--text-muted)] line-clamp-1">
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
                className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleAssign}
                disabled={assign.isPending}
                className="flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
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
            <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
            <p className="text-sm text-[var(--text-secondary)]">AI 팀을 배정하는 중...</p>
          </div>
        )}

        {/* Step: Drafting */}
        {step === "drafting" && (
          <div className="flex flex-col items-center gap-3 py-10">
            <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
            <p className="text-sm text-[var(--text-secondary)]">파이프라인을 시작하는 중...</p>
            <p className="text-xs text-[var(--text-muted)]">초안 생성 후 자동으로 진행됩니다</p>
          </div>
        )}

        {/* Step: Pushing to Linear */}
        {step === "pushing" && (
          <div className="flex flex-col items-center gap-3 py-10">
            <Loader2 className="h-8 w-8 animate-spin text-sky-600" />
            <p className="text-sm text-[var(--text-secondary)]">Linear에 이슈를 등록하는 중...</p>
            <p className="text-xs text-[var(--text-muted)]">서브태스크를 Linear 이슈로 변환합니다</p>
          </div>
        )}

        {/* Step: Done */}
        {step === "done" && (
          <>
            <div className="flex flex-col items-center gap-3 py-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
                <Check className="h-6 w-6 text-emerald-700" />
              </div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                작업이 생성되었습니다!
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                {subtasks.length}개 서브태스크가 배정되었습니다
              </p>
            </div>

            {/* Linear 결과 */}
            {linearResult && linearResult.count > 0 && (
              <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
                <div className="mb-1.5 flex items-center gap-1.5">
                  <Link2 className="h-3.5 w-3.5 text-emerald-700" />
                  <p className="text-xs font-medium text-emerald-700">
                    Linear 이슈 등록 완료 ({linearResult.count}개)
                  </p>
                  {linearResult.initial_state_applied && (
                    <span className="ml-auto rounded-full bg-amber-600 px-2 py-0.5 text-[10px] font-semibold text-white">
                      Wait (검수 대기)
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {linearResult.created_urls.map((url, i) => (
                    <a
                      key={url}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-emerald-700 underline hover:text-emerald-600"
                    >
                      {linearResult.created_identifiers[i] ?? url}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {linearError && (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
                <div className="mb-1 flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-700" />
                  <p className="text-xs font-medium text-amber-700">Linear 이슈 등록 실패</p>
                </div>
                <p className="text-xs text-amber-700">
                  {linearError.includes("자격증명") ? (
                    <>
                      Linear API 키가 설정되지 않았습니다.{" "}
                      <Link href="/settings/linear" className="underline hover:text-amber-600">
                        설정 → Linear에서 연결하세요 →
                      </Link>
                    </>
                  ) : (
                    linearError
                  )}
                </p>
              </div>
            )}

            <div className="flex justify-center">
              <button
                type="button"
                onClick={handleDone}
                className="rounded-lg bg-zinc-900 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
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
