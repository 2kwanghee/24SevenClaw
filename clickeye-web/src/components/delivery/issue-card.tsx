"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText } from "lucide-react";

import { SubTaskDetailModal } from "@/components/ai-team/subtask-detail-modal";
import { useMockMode } from "@/stores/mock-mode-store";
import type { SubTaskResponse, SubTaskRole } from "@/lib/api-client";

const ROLE_CLS: Record<SubTaskRole, string> = {
  architect: "bg-[var(--bg-hover)] text-[var(--text-secondary)]",
  frontend: "bg-[var(--bg-hover)] text-[var(--text-secondary)]",
  backend: "bg-[var(--bg-hover)] text-[var(--text-secondary)]",
  qa: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
  security: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
  devops: "bg-[var(--bg-hover)] text-[var(--text-secondary)]",
  reviewer: "bg-[var(--accent-soft)] text-[var(--accent)]",
};

interface IssueCardProps {
  subtask: SubTaskResponse;
  sessionId: string;
  orderNum: number;
  total: number;
  dependencyMap: Map<string, SubTaskResponse>;
}

export function IssueCard({
  subtask,
  sessionId,
  orderNum,
  total,
  dependencyMap,
}: IssueCardProps) {
  const [open, setOpen] = useState(false);
  const t = useTranslations("delivery");
  const mock = useMockMode((s) => s.enabled);

  const roleCls =
    ROLE_CLS[subtask.assigned_role] ??
    "bg-[var(--bg-hover)] text-[var(--text-secondary)]";
  const roleLabel = t.has(`issues.role.${subtask.assigned_role}`)
    ? t(`issues.role.${subtask.assigned_role}`)
    : subtask.assigned_role;
  const identifier = subtask.linear_identifier ?? `#${orderNum}`;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex flex-col gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 text-left transition-colors hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] font-bold text-[var(--accent)]">
            {identifier}
          </span>
        </div>
        <p className="line-clamp-2 text-[13px] font-medium leading-snug text-[var(--text-primary)]">
          {subtask.title}
        </p>
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${roleCls}`}
          >
            {roleLabel}
          </span>
          {subtask.artifact_id && (
            <span className="ml-auto inline-flex items-center gap-1 text-[10.5px] text-[var(--text-muted)]">
              <FileText className="h-3 w-3" aria-hidden="true" />
              {t("issues.artifact")}
            </span>
          )}
        </div>
      </button>

      <SubTaskDetailModal
        subtask={subtask}
        sessionId={sessionId}
        orderNum={orderNum}
        total={total}
        dependencyMap={dependencyMap}
        open={open}
        onClose={() => setOpen(false)}
        mock={mock}
      />
    </>
  );
}
