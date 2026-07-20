"use client";

import {
  AlertTriangle,
  Bot,
  Code2,
  Cpu,
  ExternalLink,
  Eye,
  Loader2,
  RotateCcw,
  Server,
  Shield,
  TestTube2,
  Wrench,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

import { BaseModal } from "@/components/common/base-modal";
import { useApproveSubtask, useResetSubtaskToWait, useSyncLinearStates } from "@/hooks/use-orchestrator";
import type { LinearTeamState, SubTaskResponse } from "@/lib/api-client";

const ROLE_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  architect: { label: "아키텍트", icon: <Cpu className="h-3.5 w-3.5" />, color: "text-[var(--text-secondary)]", bg: "bg-[var(--bg-hover)]" },
  frontend:  { label: "프론트엔드", icon: <Code2 className="h-3.5 w-3.5" />, color: "text-cyan-700", bg: "bg-cyan-50" },
  backend:   { label: "백엔드", icon: <Server className="h-3.5 w-3.5" />, color: "text-blue-700", bg: "bg-blue-50" },
  qa:        { label: "QA", icon: <TestTube2 className="h-3.5 w-3.5" />, color: "text-emerald-700", bg: "bg-emerald-50" },
  security:  { label: "보안", icon: <Shield className="h-3.5 w-3.5" />, color: "text-amber-700", bg: "bg-amber-50" },
  devops:    { label: "DevOps", icon: <Wrench className="h-3.5 w-3.5" />, color: "text-orange-700", bg: "bg-orange-50" },
  reviewer:  { label: "리뷰어", icon: <Eye className="h-3.5 w-3.5" />, color: "text-pink-700", bg: "bg-pink-50" },
};

const md: Components = {
  h1: ({ children }) => <h1 className="mb-4 mt-0 text-base font-bold text-[var(--text-primary)]">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-3 mt-5 text-sm font-semibold text-[var(--text-primary)]">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-2 mt-4 text-sm font-semibold text-[var(--text-primary)]">{children}</h3>,
  p:  ({ children }) => <p className="mb-2.5 text-sm leading-relaxed text-[var(--text-secondary)]">{children}</p>,
  ul: ({ children }) => <ul className="mb-2.5 list-disc space-y-1 pl-5 text-sm text-[var(--text-secondary)]">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2.5 list-decimal space-y-1 pl-5 text-sm text-[var(--text-secondary)]">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>,
  hr: () => <hr className="my-4 border-[var(--border-subtle)]" />,
  code: ({ children, className }) => {
    const isBlock = Boolean(className?.includes("language-"));
    return isBlock
      ? <code className="font-mono text-[var(--text-primary)]">{children}</code>
      : <code className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 font-mono text-xs text-[var(--text-primary)]">{children}</code>;
  },
  pre: ({ children }) => (
    <pre className="mb-2.5 overflow-x-auto rounded-lg bg-[var(--bg-hover)] p-3 text-xs">{children}</pre>
  ),
};

interface SubTaskDetailModalProps {
  subtask: SubTaskResponse;
  orderNum: number;
  total: number;
  dependencyMap: Map<string, SubTaskResponse>;
  open: boolean;
  onClose: () => void;
  sessionId?: string;
  teamStates?: LinearTeamState[];
  /** 목업 모드 — true면 승인/리셋 등 실제 변경 액션을 비활성화한다. 기본 false. */
  mock?: boolean;
}

export function SubTaskDetailModal({
  subtask,
  orderNum,
  total,
  dependencyMap,
  open,
  onClose,
  sessionId,
  mock = false,
}: SubTaskDetailModalProps) {
  const role = ROLE_CONFIG[subtask.assigned_role] ?? {
    label: subtask.assigned_role,
    icon: <Bot className="h-3.5 w-3.5" />,
    color: "text-[var(--text-muted)]",
    bg: "bg-[var(--bg-hover)]",
  };

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

  const unapprovedDeps = subtask.depends_on.filter((depTitle) => {
    const dep = dependencyMap.get(depTitle);
    return dep ? dep.status !== "approved" : true;
  });
  const hasUnresolvedDeps = unapprovedDeps.length > 0;

  return (
    <BaseModal
      open={open}
      onClose={onClose}
      size="lg"
      titleId="subtask-detail-title"
      title={
        <div className="flex items-center gap-2 min-w-0">
          <div className={`flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${role.bg} ${role.color}`}>
            {role.icon}
            {role.label}
          </div>
          <span className="truncate text-sm font-semibold text-[var(--text-primary)]">
            {subtask.title}
          </span>
        </div>
      }
    >
      <div className="px-6 py-4">
        {/* 메타 행 */}
        <div className="mb-4 flex flex-wrap items-center gap-2 text-[11px]">
          <span className="rounded bg-[var(--bg-hover)] px-2 py-0.5 font-medium text-[var(--text-secondary)]">
            {orderNum} / {total}
          </span>
          {subtask.linear_identifier && (
            <span className="rounded bg-[var(--bg-hover)] px-2 py-0.5 font-mono text-[var(--text-muted)]">
              {subtask.linear_identifier}
            </span>
          )}
          {subtask.linear_state && (
            <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-700">
              {subtask.linear_state}
            </span>
          )}
        </div>

        {/* 의존성 섹션 */}
        {subtask.depends_on.length > 0 && (
          <div className="mb-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-3">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              선행 태스크
            </p>
            <ul className="space-y-1">
              {subtask.depends_on.map((depTitle) => {
                const dep = dependencyMap.get(depTitle);
                const approved = dep?.status === "approved";
                return (
                  <li key={depTitle} className="flex items-center gap-2 text-xs">
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${approved ? "bg-emerald-500" : "bg-amber-400"}`} />
                    <span className="text-[var(--text-secondary)]">{depTitle}</span>
                    {dep && (
                      <span className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        approved
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-amber-50 text-amber-700"
                      }`}>
                        {approved ? "승인됨" : "미승인"}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* 본문 마크다운 */}
        {subtask.description ? (
          <div className="prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>
              {subtask.description}
            </ReactMarkdown>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">상세 설명이 없습니다.</p>
        )}

        {/* 액션 푸터 — sessionId가 주어질 때만(딜리버리 콘솔) 렌더, ai-team은 읽기 전용 */}
        {sessionId && (canApprove || canReset) && (
          <div className="mt-5 flex items-center justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
            {canReset && (
              <button
                type="button"
                disabled={resetMutation.isPending || mock}
                title={mock ? "목업 모드에서는 비활성" : undefined}
                onClick={() => resetMutation.mutate({ sessionId, subtaskId: subtask.id })}
                className="flex items-center gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700 transition-colors hover:bg-amber-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 disabled:opacity-50 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
              >
                {resetMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                대기로 복귀
              </button>
            )}
            {canApprove && (
              <button
                type="button"
                disabled={approveMutation.isPending || mock}
                title={mock ? "목업 모드에서는 비활성" : undefined}
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
                className="flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-violet-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 disabled:opacity-50"
              >
                {approveMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                ) : hasUnresolvedDeps ? (
                  <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                {isLinearUnregistered ? "승인" : "큐 등록"}
              </button>
            )}
          </div>
        )}
      </div>
    </BaseModal>
  );
}
