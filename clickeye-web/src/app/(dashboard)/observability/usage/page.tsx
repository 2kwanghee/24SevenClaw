"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AlertCircle, ListOrdered } from "lucide-react";
import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { BentoCard } from "@/components/ui/bento";
import { useUsagePivot } from "@/hooks/use-observability";
import { ApiClientError, type UsageGroupBy } from "@/lib/api-client";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

const GROUP_BY_OPTIONS: UsageGroupBy[] = [
  "project_id",
  "seat_id",
  "model",
  "request_kind",
];

function UsageContent() {
  const t = useTranslations("observability.usage");
  const router = useRouter();

  const [groupBy, setGroupBy] = useState<UsageGroupBy>("model");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const { data, isLoading, error } = useUsagePivot({
    groupBy,
    from: from || undefined,
    to: to || undefined,
  });

  const canDrilldown = groupBy === "project_id";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
          <ListOrdered className="h-5 w-5 text-[var(--accent)]" />
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
            {t("filter.groupBy")}
          </label>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as UsageGroupBy)}
            className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--border-medium)]"
          >
            {GROUP_BY_OPTIONS.map((g) => (
              <option key={g} value={g}>
                {t(`filter.groupByOption.${g}`)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
            {t("filter.from")}
          </label>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:border-[var(--border-medium)]"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
            {t("filter.to")}
          </label>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
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
                  {t(`filter.groupByOption.${groupBy}`)}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">
                  {t("col.inputTokens")}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">
                  {t("col.outputTokens")}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">
                  {t("col.cost")}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">
                  {t("col.requestCount")}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.buckets.map((bucket, i) => (
                <tr
                  key={`${bucket.key ?? "null"}-${i}`}
                  onClick={
                    canDrilldown && bucket.key
                      ? () =>
                          router.push(
                            `/observability/runs?project_id=${encodeURIComponent(bucket.key ?? "")}`,
                          )
                      : undefined
                  }
                  className={`border-b border-[var(--border-subtle)] last:border-b-0 ${
                    canDrilldown && bucket.key
                      ? "cursor-pointer hover:bg-[var(--bg-hover)]"
                      : ""
                  }`}
                >
                  <td className="px-4 py-3 text-sm font-medium text-[var(--text-primary)]">
                    {bucket.key ?? t("unknownKey")}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-secondary)]">
                    {bucket.input_tokens.toLocaleString("ko-KR")}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-secondary)]">
                    {bucket.output_tokens.toLocaleString("ko-KR")}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-secondary)]">
                    {bucket.cost ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-secondary)]">
                    {bucket.request_count.toLocaleString("ko-KR")}
                  </td>
                </tr>
              ))}
              {data.buckets.length === 0 && (
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
            {data.buckets.length > 0 && (
              <tfoot>
                <tr className="border-t border-[var(--border-subtle)] bg-[var(--bg-hover)] font-medium">
                  <td className="px-4 py-3 text-sm text-[var(--text-primary)]">
                    {t("total")}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-primary)]">
                    {data.total_input_tokens.toLocaleString("ko-KR")}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-primary)]">
                    {data.total_output_tokens.toLocaleString("ko-KR")}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-primary)]">
                    {data.total_cost ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right text-xs tabular-nums text-[var(--text-primary)]">
                    {data.total_request_count.toLocaleString("ko-KR")}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </BentoCard>
      )}
    </div>
  );
}

export default function ObservabilityUsagePage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <UsageContent />
    </RoleGuard>
  );
}
