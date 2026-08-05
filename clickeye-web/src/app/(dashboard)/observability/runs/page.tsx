"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Activity, AlertCircle, AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { BentoCard } from "@/components/ui/bento";
import {
  hasModelMismatch,
  OUTCOME_TONE,
  PipelineUsageBar,
} from "@/components/delivery/pipeline-run-flow";
import { PipelineRunThread } from "@/components/delivery/pipeline-run-thread";
import { useRunDetail, useRunsList } from "@/hooks/use-observability";
import { ApiClientError, type PipelineRun } from "@/lib/api-client";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

function OutcomeBadge({ run }: { run: PipelineRun }) {
  const tPipeline = useTranslations("delivery.pipeline");
  const outcome = run.outcome ?? "unknown";
  const tone = OUTCOME_TONE[outcome] ?? OUTCOME_TONE.unknown;
  const label = tPipeline.has(`outcome.${outcome}`)
    ? tPipeline(`outcome.${outcome}`)
    : outcome;
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${tone}`}>
      {label}
    </span>
  );
}

function DurationLabel({ run }: { run: PipelineRun }) {
  const tPipeline = useTranslations("delivery.pipeline");
  if (run.duration_s === null || run.duration_s === undefined) return <>—</>;
  return <>{tPipeline("durationSec", { seconds: run.duration_s })}</>;
}

function RunDetailPanel({ issueKey }: { issueKey: string | null }) {
  const t = useTranslations("observability.runs");
  const { data } = useRunDetail(issueKey ?? "", !!issueKey);

  return (
    <BentoCard className="space-y-4">
      <h2 className="text-sm font-semibold text-[var(--text-primary)]">
        {t("detail.title")}
      </h2>
      {!issueKey && (
        <p className="text-sm text-[var(--text-muted)]">{t("detail.empty")}</p>
      )}
      {issueKey && data && (
        <div className="space-y-4">
          {data.items.map((run) => (
            <div key={run.run_id} className="space-y-3">
              <PipelineUsageBar runs={[run]} />
              <PipelineRunThread run={run} />
            </div>
          ))}
        </div>
      )}
    </BentoCard>
  );
}

function RunsContent() {
  const t = useTranslations("observability.runs");
  const searchParams = useSearchParams();

  const [issueKey, setIssueKey] = useState("");
  const [projectId, setProjectId] = useState(
    searchParams.get("project_id") ?? "",
  );
  const [selectedIssueKey, setSelectedIssueKey] = useState<string | null>(null);

  const { data, isLoading, error } = useRunsList({
    issueKey: issueKey || undefined,
    projectId: projectId || undefined,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
          <Activity className="h-5 w-5 text-[var(--accent)]" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            {t("pageTitle")}
          </h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            {t("pageDescription")}
          </p>
        </div>
      </div>

      {/* 필터 */}
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
            {t("filter.issueKey")}
          </label>
          <input
            type="text"
            value={issueKey}
            onChange={(e) => setIssueKey(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--border-medium)]"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
            {t("filter.projectId")}
          </label>
          <input
            type="text"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--border-medium)]"
          />
        </div>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-sm text-[var(--text-muted)]">
          {t("loading")}
        </div>
      )}

      {error && isFeatureDisabled(error) && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          {t("featureDisabled")}
        </div>
      )}

      {error && !isFeatureDisabled(error) && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {(error as Error).message || t("error")}
        </div>
      )}

      {data && (
        <BentoCard className="overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.issueKey")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.outcome")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.duration")}
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-[var(--text-muted)]">
                  {t("col.modelMismatch")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.startedAt")}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((run) => (
                <tr
                  key={run.run_id}
                  onClick={() => setSelectedIssueKey(run.issue_key)}
                  className={`cursor-pointer border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--bg-hover)] ${
                    selectedIssueKey === run.issue_key
                      ? "bg-[var(--bg-hover)]"
                      : ""
                  }`}
                >
                  <td className="px-4 py-3 text-sm font-medium text-[var(--text-primary)]">
                    {run.issue_key}
                  </td>
                  <td className="px-4 py-3">
                    <OutcomeBadge run={run} />
                  </td>
                  <td className="px-4 py-3 text-xs tabular-nums text-[var(--text-secondary)]">
                    <DurationLabel run={run} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    {(run.model_mismatch || hasModelMismatch(run.events)) && (
                      <AlertTriangle className="mx-auto h-4 w-4 text-amber-500" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">
                    {run.started_at
                      ? new Date(run.started_at).toLocaleString("ko-KR")
                      : "—"}
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-12 text-center text-sm text-[var(--text-muted)]"
                  >
                    {t("empty")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </BentoCard>
      )}

      <RunDetailPanel issueKey={selectedIssueKey} />
    </div>
  );
}

function RunsPageInner() {
  return <RunsContent />;
}

export default function ObservabilityRunsPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-20">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent)]" />
          </div>
        }
      >
        <RunsPageInner />
      </Suspense>
    </RoleGuard>
  );
}
