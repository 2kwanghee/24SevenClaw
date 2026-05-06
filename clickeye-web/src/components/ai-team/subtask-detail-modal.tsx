"use client";

import {
  Bot,
  Code2,
  Cpu,
  Eye,
  Server,
  Shield,
  TestTube2,
  Wrench,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

import { BaseModal } from "@/components/common/base-modal";
import type { SubTaskResponse } from "@/lib/api-client";

const ROLE_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  architect: { label: "아키텍트", icon: <Cpu className="h-3.5 w-3.5" />, color: "text-zinc-700", bg: "bg-zinc-100" },
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
}

export function SubTaskDetailModal({
  subtask,
  orderNum,
  total,
  dependencyMap,
  open,
  onClose,
}: SubTaskDetailModalProps) {
  const role = ROLE_CONFIG[subtask.assigned_role] ?? {
    label: subtask.assigned_role,
    icon: <Bot className="h-3.5 w-3.5" />,
    color: "text-[var(--text-muted)]",
    bg: "bg-zinc-100",
  };

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
          <span className="rounded bg-zinc-100 px-2 py-0.5 font-medium text-zinc-600">
            {orderNum} / {total}
          </span>
          {subtask.linear_identifier && (
            <span className="rounded bg-zinc-100 px-2 py-0.5 font-mono text-zinc-500">
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
      </div>
    </BaseModal>
  );
}
