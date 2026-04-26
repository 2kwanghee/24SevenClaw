"use client";

import {
  Bot,
  Code2,
  Cpu,
  Eye,
  ExternalLink,
  Loader2,
  Server,
  Shield,
  TestTube2,
  Wrench,
} from "lucide-react";

import { useApproveSubtask } from "@/hooks/use-orchestrator";
import type { SubTaskResponse } from "@/lib/api-client";

const ROLE_CONFIG: Record<
  string,
  { label: string; icon: React.ReactNode; color: string; bg: string }
> = {
  architect: {
    label: "아키텍트",
    icon: <Cpu className="h-3.5 w-3.5" />,
    color: "text-zinc-700",
    bg: "bg-zinc-100",
  },
  frontend: {
    label: "프론트엔드",
    icon: <Code2 className="h-3.5 w-3.5" />,
    color: "text-cyan-700",
    bg: "bg-cyan-50",
  },
  backend: {
    label: "백엔드",
    icon: <Server className="h-3.5 w-3.5" />,
    color: "text-blue-700",
    bg: "bg-blue-50",
  },
  qa: {
    label: "QA",
    icon: <TestTube2 className="h-3.5 w-3.5" />,
    color: "text-emerald-700",
    bg: "bg-emerald-50",
  },
  security: {
    label: "보안",
    icon: <Shield className="h-3.5 w-3.5" />,
    color: "text-amber-700",
    bg: "bg-amber-50",
  },
  devops: {
    label: "DevOps",
    icon: <Wrench className="h-3.5 w-3.5" />,
    color: "text-orange-700",
    bg: "bg-orange-50",
  },
  reviewer: {
    label: "리뷰어",
    icon: <Eye className="h-3.5 w-3.5" />,
    color: "text-pink-700",
    bg: "bg-pink-50",
  },
};

const STATUS_CONFIG: Record<
  string,
  { label: string; cls: string }
> = {
  pending: { label: "대기", cls: "bg-zinc-100 text-zinc-600" },
  in_progress: { label: "진행 중", cls: "bg-blue-50 text-blue-700" },
  completed: { label: "완료", cls: "bg-emerald-50 text-emerald-700" },
  failed: { label: "실패", cls: "bg-red-50 text-red-700" },
  blocked: { label: "차단됨", cls: "bg-amber-50 text-amber-700" },
};

const LINEAR_STATE_CONFIG: Record<string, { label: string; cls: string }> = {
  Wait: { label: "검수 대기", cls: "bg-amber-50 text-amber-700 border border-amber-200" },
  Queued: { label: "큐 등록됨", cls: "bg-violet-50 text-violet-700 border border-violet-200" },
  "In Progress": { label: "개발 중", cls: "bg-blue-50 text-blue-700 border border-blue-200" },
  "In Review": { label: "리뷰 중", cls: "bg-pink-50 text-pink-700 border border-pink-200" },
  Done: { label: "완료", cls: "bg-emerald-50 text-emerald-700 border border-emerald-200" },
};

interface SubTaskCardProps {
  subtask: SubTaskResponse;
  sessionId?: string;
}

export function SubTaskCard({ subtask, sessionId }: SubTaskCardProps) {
  const role = ROLE_CONFIG[subtask.assigned_role] ?? {
    label: subtask.assigned_role,
    icon: <Bot className="h-3.5 w-3.5" />,
    color: "text-[var(--text-muted)]",
    bg: "bg-zinc-100",
  };
  const status = STATUS_CONFIG[subtask.status] ?? STATUS_CONFIG.pending;
  const linearState = subtask.linear_state
    ? (LINEAR_STATE_CONFIG[subtask.linear_state] ?? { label: subtask.linear_state, cls: "bg-zinc-100 text-zinc-600" })
    : null;

  const approveMutation = useApproveSubtask();
  const canApprove = !!subtask.linear_issue_id && subtask.linear_state === "Wait" && !!sessionId;

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 transition-colors hover:bg-[var(--bg-hover)]">
      {/* 역할 배지 + 상태 */}
      <div className="flex items-center justify-between">
        <div className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${role.bg} ${role.color}`}>
          {role.icon}
          {role.label}
        </div>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${status.cls}`}>
          {status.label}
        </span>
      </div>

      {/* 제목 */}
      <p className="mt-3 text-sm font-medium text-[var(--text-primary)] line-clamp-2">
        {subtask.title}
      </p>

      {/* 미리보기 (result_summary 또는 description) */}
      {(subtask.result_summary || subtask.description) && (
        <p className="mt-1.5 text-xs text-[var(--text-muted)] line-clamp-2">
          {subtask.result_summary ?? subtask.description}
        </p>
      )}

      {/* 의존성 표시 */}
      {subtask.depends_on.length > 0 && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
          <span>의존:</span>
          <span className="truncate">{subtask.depends_on.length}개 태스크</span>
        </div>
      )}

      {/* Linear 연동 정보 */}
      {subtask.linear_identifier && (
        <div className="mt-3 flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono text-[var(--text-muted)]">
              {subtask.linear_identifier}
            </span>
            {linearState && (
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${linearState.cls}`}>
                {linearState.label}
              </span>
            )}
          </div>

          {canApprove ? (
            <button
              type="button"
              disabled={approveMutation.isPending}
              onClick={() =>
                approveMutation.mutate({ sessionId, subtaskId: subtask.id })
              }
              className="flex items-center gap-1 rounded-md bg-violet-600 px-2 py-1 text-[11px] font-semibold text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
            >
              {approveMutation.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <ExternalLink className="h-3 w-3" />
              )}
              큐 등록
            </button>
          ) : subtask.linear_state && subtask.linear_state !== "Wait" ? (
            <span className="text-[10px] text-[var(--text-muted)]">승인됨</span>
          ) : null}
        </div>
      )}
    </div>
  );
}
