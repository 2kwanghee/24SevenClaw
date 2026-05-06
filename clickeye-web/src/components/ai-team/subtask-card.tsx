"use client";

import { useState } from "react";

import {
  AlertTriangle,
  Bot,
  Code2,
  Cpu,
  Eye,
  ExternalLink,
  Loader2,
  RotateCcw,
  Server,
  Shield,
  TestTube2,
  Wrench,
} from "lucide-react";

import { useApproveSubtask, useResetSubtaskToWait, useSyncLinearStates } from "@/hooks/use-orchestrator";
import type { LinearTeamState, SubTaskResponse } from "@/lib/api-client";
import { SubTaskDetailModal } from "./subtask-detail-modal";

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

const LINEAR_TYPE_CLS: Record<string, string> = {
  triage:    "bg-amber-50 text-amber-700 border border-amber-200",
  backlog:   "bg-zinc-100 text-zinc-500 border border-zinc-200",
  unstarted: "bg-zinc-100 text-zinc-600 border border-zinc-200",
  started:   "bg-blue-50 text-blue-700 border border-blue-200",
  completed: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  cancelled: "bg-red-50 text-red-600 border border-red-200",
};

const LINEAR_TYPE_FALLBACK = "bg-zinc-100 text-zinc-600 border border-zinc-200";

function getLinearStateCls(stateName: string, teamStates: LinearTeamState[]): string {
  const matched = teamStates.find((s) => s.name === stateName);
  if (matched) return LINEAR_TYPE_CLS[matched.type] ?? LINEAR_TYPE_FALLBACK;
  const lower = stateName.toLowerCase();
  if (lower === "done" || lower === "completed") return LINEAR_TYPE_CLS.completed;
  if (lower.includes("progress") || lower.includes("started")) return LINEAR_TYPE_CLS.started;
  if (lower === "wait" || lower.includes("triage")) return LINEAR_TYPE_CLS.triage;
  if (lower.includes("review")) return "bg-pink-50 text-pink-700 border border-pink-200";
  if (lower.includes("queue") || lower.includes("backlog")) return LINEAR_TYPE_CLS.backlog;
  if (lower === "cancelled" || lower === "canceled") return LINEAR_TYPE_CLS.cancelled;
  return LINEAR_TYPE_FALLBACK;
}

interface SubTaskCardProps {
  subtask: SubTaskResponse;
  sessionId?: string;
  teamStates?: LinearTeamState[];
  orderNum: number;
  total: number;
  dependencyMap: Map<string, SubTaskResponse>;
  isNextRecommended: boolean;
}

export function SubTaskCard({
  subtask,
  sessionId,
  teamStates = [],
  orderNum,
  total,
  dependencyMap,
  isNextRecommended,
}: SubTaskCardProps) {
  const [detailOpen, setDetailOpen] = useState(false);

  const role = ROLE_CONFIG[subtask.assigned_role] ?? {
    label: subtask.assigned_role,
    icon: <Bot className="h-3.5 w-3.5" />,
    color: "text-[var(--text-muted)]",
    bg: "bg-zinc-100",
  };
  const status = STATUS_CONFIG[subtask.status] ?? STATUS_CONFIG.pending;
  const linearStateName = subtask.linear_state ?? null;
  const linearStateCls = linearStateName
    ? getLinearStateCls(linearStateName, teamStates)
    : null;

  const approveMutation = useApproveSubtask();
  const resetMutation = useResetSubtaskToWait();
  const syncLinearStates = useSyncLinearStates(sessionId ?? "");

  const isLinearUnregistered = !subtask.linear_issue_id;
  const canApprove = !!sessionId && (
    (!!subtask.linear_issue_id && subtask.linear_state === "Backlog") ||
    (isLinearUnregistered && subtask.status === "pending")
  );
  const canReset =
    !!subtask.linear_issue_id &&
    !!sessionId &&
    ["Todo", "Backlog"].includes(subtask.linear_state ?? "");

  // 의존성 분석
  const unapprovedDeps = subtask.depends_on.filter((depTitle) => {
    const dep = dependencyMap.get(depTitle);
    return dep ? dep.status !== "approved" : true;
  });
  const hasUnresolvedDeps = unapprovedDeps.length > 0;
  const approvedDepsCount = subtask.depends_on.filter((depTitle) => {
    const dep = dependencyMap.get(depTitle);
    return dep?.status === "approved";
  }).length;

  return (
    <>
      <div className={`rounded-xl border bg-[var(--bg-surface)] p-4 transition-colors hover:bg-[var(--bg-hover)] ${
        isNextRecommended
          ? "border-violet-400 ring-1 ring-violet-400/50"
          : "border-[var(--border-subtle)]"
      }`}>
        {/* 역할 배지 + 순번 + 상태 + 상세보기 */}
        <div className="flex items-center justify-between gap-1.5">
          <div className="flex min-w-0 items-center gap-1.5">
            <div className={`flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${role.bg} ${role.color}`}>
              {role.icon}
              {role.label}
            </div>
            <span className="shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-medium text-zinc-500">
              {orderNum}/{total}
            </span>
            {isNextRecommended && (
              <span className="shrink-0 rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-semibold text-violet-700">
                다음 추천
              </span>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${status.cls}`}>
              {status.label}
            </span>
            <button
              type="button"
              onClick={() => setDetailOpen(true)}
              title="상세 보기"
              className="rounded-md p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              <Eye className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* 제목 */}
        <p className="mt-3 text-sm font-medium text-[var(--text-primary)] line-clamp-2">
          {subtask.title}
        </p>

        {/* 미리보기 */}
        {(subtask.result_summary || subtask.description) && (
          <p className="mt-1.5 text-xs text-[var(--text-muted)] line-clamp-2">
            {subtask.result_summary ?? subtask.description}
          </p>
        )}

        {/* 의존성 표시 */}
        {subtask.depends_on.length > 0 && (
          <div className="mt-2 flex items-center gap-1.5">
            {hasUnresolvedDeps ? (
              <span
                className="flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700"
                title={`미승인: ${unapprovedDeps.join(", ")}`}
              >
                <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                선행 {unapprovedDeps.length}개 미승인
              </span>
            ) : (
              <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                선행 {approvedDepsCount}개 모두 승인
              </span>
            )}
          </div>
        )}

        {/* Linear 연동 정보 */}
        <div className="mt-3 flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3">
          <div className="flex items-center gap-1.5">
            {subtask.linear_identifier ? (
              <>
                <span className="text-[10px] font-mono text-[var(--text-muted)]">
                  {subtask.linear_identifier}
                </span>
                {linearStateName && linearStateCls && (
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${linearStateCls}`}>
                    {linearStateName}
                  </span>
                )}
              </>
            ) : (
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                subtask.status === "approved"
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "bg-amber-50 text-amber-700 border border-amber-200"
              }`}>
                {subtask.status === "approved" ? "승인됨 — Linear 등록 중" : "Linear 미등록(검토 중)"}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {canApprove && (
              <button
                type="button"
                disabled={approveMutation.isPending}
                onClick={() =>
                  approveMutation.mutate(
                    { sessionId, subtaskId: subtask.id },
                    {
                      onSuccess: () => {
                        if (sessionId && !isLinearUnregistered && !syncLinearStates.isPending) {
                          syncLinearStates.mutate();
                        }
                      },
                    },
                  )
                }
                className="flex items-center gap-1 rounded-md bg-violet-600 px-2 py-1 text-[11px] font-semibold text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
              >
                {approveMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : hasUnresolvedDeps ? (
                  <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                ) : (
                  <ExternalLink className="h-3 w-3" />
                )}
                {isLinearUnregistered ? "승인" : "큐 등록"}
              </button>
            )}
            {canReset && (
              <button
                type="button"
                disabled={resetMutation.isPending}
                onClick={() =>
                  resetMutation.mutate({ sessionId, subtaskId: subtask.id })
                }
                className="flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-700 transition-colors hover:bg-amber-100 disabled:opacity-50"
              >
                {resetMutation.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <RotateCcw className="h-3 w-3" />
                )}
                대기로 복귀
              </button>
            )}
            {!canApprove && !canReset && linearStateName && linearStateName !== "Backlog" && (
              <span className="text-[10px] text-[var(--text-muted)]">
                {linearStateName}
              </span>
            )}
          </div>
        </div>
      </div>

      <SubTaskDetailModal
        subtask={subtask}
        orderNum={orderNum}
        total={total}
        dependencyMap={dependencyMap}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      />
    </>
  );
}
