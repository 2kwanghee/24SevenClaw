"use client";

import { AlertCircle, LayoutDashboard } from "lucide-react";
import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { BentoCard, BentoGrid } from "@/components/ui/bento";
import { useObservabilitySummary } from "@/hooks/use-observability";
import { ApiClientError } from "@/lib/api-client";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

/** 상태 → 색 톤. 알려지지 않은 상태값은 muted 로 안전 폴백한다. */
const STATUS_TONES: Record<string, string> = {
  active: "bg-emerald-500",
  completed: "bg-[var(--accent)]",
  pending_review: "bg-amber-500",
  accepted: "bg-blue-500",
  rejected: "bg-[var(--text-muted)]",
};

function toneFor(key: string): string {
  return STATUS_TONES[key] ?? "bg-[var(--text-muted)]";
}

function StatusBarList({
  data,
  emptyLabel,
}: {
  data: Record<string, number>;
  emptyLabel: string;
}) {
  const entries = Object.entries(data);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  if (entries.length === 0 || total === 0) {
    return <p className="text-xs text-[var(--text-muted)]">{emptyLabel}</p>;
  }

  return (
    <div className="mt-4 space-y-3">
      {entries.map(([key, value]) => {
        const pct = total > 0 ? Math.round((value / total) * 100) : 0;
        return (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-[var(--text-secondary)]">{key}</span>
              <span className="tabular-nums text-[var(--text-muted)]">{value}</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--bg-hover)]">
              <div
                className={`h-full rounded-full ${toneFor(key)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SuccessRateDonut({
  rate,
  successCount,
  failureCount,
}: {
  rate: number | null;
  successCount: number;
  failureCount: number;
}) {
  const t = useTranslations("observability.dashboard");
  const pct = rate !== null ? Math.round(rate * 100) : null;

  if (pct === null && successCount === 0 && failureCount === 0) {
    return <p className="text-xs text-[var(--text-muted)]">{t("noRuns")}</p>;
  }

  const displayPct = pct ?? 0;

  return (
    <div className="mt-4 flex items-center gap-5">
      <div
        className="relative h-24 w-24 shrink-0 rounded-full"
        style={{
          background: `conic-gradient(var(--accent) ${displayPct}%, var(--bg-hover) ${displayPct}% 100%)`,
        }}
        role="img"
        aria-label={t("successRateAria", { pct: displayPct })}
      >
        <div className="absolute inset-2 flex items-center justify-center rounded-full bg-[var(--bg-surface)]">
          <span className="text-lg font-semibold tabular-nums text-[var(--text-primary)]">
            {pct !== null ? `${pct}%` : "—"}
          </span>
        </div>
      </div>
      <div className="space-y-1 text-xs">
        <p className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="text-[var(--text-secondary)]">
            {t("success")}: <span className="tabular-nums">{successCount}</span>
          </span>
        </p>
        <p className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          <span className="text-[var(--text-secondary)]">
            {t("failure")}: <span className="tabular-nums">{failureCount}</span>
          </span>
        </p>
      </div>
    </div>
  );
}

function DashboardContent() {
  const t = useTranslations("observability.dashboard");
  const { data, isLoading, error } = useObservabilitySummary();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
          <LayoutDashboard className="h-5 w-5 text-[var(--accent)]" />
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
        <BentoGrid>
          <BentoCard title={t("projectsByStatus")}>
            <StatusBarList
              data={data.projects_by_status}
              emptyLabel={t("empty")}
            />
          </BentoCard>

          <BentoCard title={t("intakeFunnel")}>
            <StatusBarList data={data.intake_by_status} emptyLabel={t("empty")} />
          </BentoCard>

          <BentoCard title={t("pipelineSuccessRate")}>
            <SuccessRateDonut
              rate={data.pipeline_run_success_rate}
              successCount={data.pipeline_run_success_count}
              failureCount={data.pipeline_run_failure_count}
            />
          </BentoCard>

          <BentoCard size="wide" title={t("recentDeliveryEvents")}>
            {data.recent_delivery_events.length === 0 ? (
              <p className="mt-4 text-xs text-[var(--text-muted)]">{t("empty")}</p>
            ) : (
              <ul className="mt-4 space-y-2">
                {data.recent_delivery_events.map((ev) => (
                  <li
                    key={ev.id}
                    className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-[var(--border-subtle)] pb-2 text-xs last:border-b-0 last:pb-0"
                  >
                    <span className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-2 py-0.5 font-medium text-[var(--text-secondary)]">
                      {ev.event_type}
                    </span>
                    <span className="text-[var(--text-muted)]">{ev.actor_type}</span>
                    {ev.detail && (
                      <span className="text-[var(--text-secondary)]">{ev.detail}</span>
                    )}
                    <time className="ml-auto tabular-nums text-[var(--text-muted)]">
                      {new Date(ev.created_at).toLocaleString("ko-KR")}
                    </time>
                  </li>
                ))}
              </ul>
            )}
          </BentoCard>
        </BentoGrid>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <DashboardContent />
    </RoleGuard>
  );
}
