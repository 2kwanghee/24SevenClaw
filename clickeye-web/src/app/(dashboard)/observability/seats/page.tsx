"use client";

import { AlertCircle, Coins } from "lucide-react";
import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { BentoCard, BentoGrid } from "@/components/ui/bento";
import { useSeats } from "@/hooks/use-observability";
import { ApiClientError, type SeatQuotaLatestEntry } from "@/lib/api-client";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

const SEAT_STATUS_TONES: Record<string, string> = {
  active: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  pending_login: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
  disabled: "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
};

function SeatStatusBadge({ status }: { status: string | null }) {
  const t = useTranslations("observability.seats");
  if (!status) return null;
  const tone = SEAT_STATUS_TONES[status] ?? SEAT_STATUS_TONES.disabled;
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${tone}`}>
      {t.has(`status.${status}`) ? t(`status.${status}`) : status}
    </span>
  );
}

/** 신선도 — usage_fetched_at 경과를 "n분 전" 형태로 표시 */
function freshnessLabel(
  isoTimestamp: string | null,
  t: (key: string, values?: Record<string, string | number | Date>) => string,
): string {
  if (!isoTimestamp) return t("freshness.unknown");
  const fetchedAt = new Date(isoTimestamp).getTime();
  const diffMin = Math.max(0, Math.round((Date.now() - fetchedAt) / 60000));
  if (diffMin < 1) return t("freshness.justNow");
  if (diffMin < 60) return t("freshness.minutesAgo", { count: diffMin });
  const diffHour = Math.round(diffMin / 60);
  return t("freshness.hoursAgo", { count: diffHour });
}

function WindowGauge({ entry }: { entry: SeatQuotaLatestEntry }) {
  const t = useTranslations("observability.seats");
  const pct = Math.min(100, Math.max(0, Number(entry.pct) || 0));
  const tone = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-emerald-500";
  const label = entry.scope_name ?? entry.window;

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3">
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="font-medium text-[var(--text-secondary)]">{label}</span>
        <span className="tabular-nums text-[var(--text-muted)]">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--bg-hover)]">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {entry.ahead_of_pace !== null && (
          <span
            className={`rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${
              entry.ahead_of_pace
                ? "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300"
                : "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
            }`}
          >
            {entry.ahead_of_pace ? t("aheadOfPace") : t("onPace")}
          </span>
        )}
        {entry.projected_exhaustion_at && (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            {t("projectedExhaustion", {
              at: new Date(entry.projected_exhaustion_at).toLocaleString("ko-KR"),
            })}
          </span>
        )}
        {entry.resets_at && (
          <span className="text-[10px] text-[var(--text-muted)]">
            {t("resetsAt", {
              at: new Date(entry.resets_at).toLocaleString("ko-KR"),
            })}
          </span>
        )}
      </div>
    </div>
  );
}

function SeatsContent() {
  const t = useTranslations("observability.seats");
  const { data, isLoading, error } = useSeats();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
          <Coins className="h-5 w-5 text-[var(--accent)]" />
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

      {data && data.items.length === 0 && (
        <div className="py-12 text-center text-sm text-[var(--text-muted)]">
          {t("empty")}
        </div>
      )}

      {data && data.items.length > 0 && (
        <BentoGrid>
          {data.items.map((seat) => (
            <BentoCard
              key={seat.seat_id ?? seat.account_email}
              size="lg"
              title={seat.account_email}
              description={freshnessLabel(
                seat.windows[0]?.usage_fetched_at ?? null,
                t,
              )}
              action={<SeatStatusBadge status={seat.seat_status} />}
            >
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {seat.windows.map((w) => (
                  <WindowGauge key={`${w.window}-${w.scope_name ?? ""}`} entry={w} />
                ))}
                {seat.windows.length === 0 && (
                  <p className="text-xs text-[var(--text-muted)]">
                    {t("noWindows")}
                  </p>
                )}
              </div>
              <p className="mt-3 text-xs text-[var(--text-muted)]">
                {t("usage24h", {
                  input: seat.usage_24h_input_tokens,
                  output: seat.usage_24h_output_tokens,
                })}
              </p>
            </BentoCard>
          ))}
        </BentoGrid>
      )}
    </div>
  );
}

export default function ObservabilitySeatsPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <SeatsContent />
    </RoleGuard>
  );
}
