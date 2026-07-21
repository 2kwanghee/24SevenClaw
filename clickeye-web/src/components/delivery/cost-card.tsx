"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle, Coins, Lock } from "lucide-react";

import type {
  LlmKeySourceTotals,
  LlmProjectUsageSummary,
} from "@/lib/api-client";

interface CostCardProps {
  summary: LlmProjectUsageSummary | null;
  isLoading?: boolean;
  isError?: boolean;
  restricted?: boolean;
}

function formatTokens(value: number): string {
  return value.toLocaleString("en-US");
}

/** Decimal은 JSON에서 number|string|null 로 올 수 있어 방어적으로 파싱한다. */
function formatCost(value: number | string | null): string | null {
  if (value === null || value === undefined) return null;
  const num = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(num)) return null;
  return `$${num.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function CardFrame({ children }: { children: React.ReactNode }) {
  const t = useTranslations("delivery");
  return (
    <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-[0_1px_2px_rgba(20,24,33,0.05)]">
      <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-4 py-3.5">
        <h2 className="text-[13.5px] font-bold tracking-tight text-[var(--text-primary)]">
          {t("cost.title")}
        </h2>
      </div>
      {children}
    </section>
  );
}

function KeySourceRow({ row }: { row: LlmKeySourceTotals }) {
  const t = useTranslations("delivery");
  const label = t.has(`cost.keySource.${row.key_source}`)
    ? t(`cost.keySource.${row.key_source}`)
    : row.key_source;
  const tokens = row.input_tokens + row.output_tokens;
  const cost = formatCost(row.cost);
  const isSubscription = row.key_source === "subscription_seat";

  // 정직성: 구독 시트는 정액이라 비용 미산정, 조직 키는 종량 과금.
  const detail = isSubscription
    ? t("cost.detailSubscription")
    : cost
      ? t("cost.detailMetered", { cost })
      : t("cost.detailMeteredUnknown");

  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`h-2 w-2 flex-none rounded-sm ${
          isSubscription ? "bg-[var(--text-muted)]" : "bg-[var(--accent)]"
        }`}
        aria-hidden="true"
      />
      <div className="flex min-w-0 flex-col">
        <span className="truncate text-xs font-medium text-[var(--text-primary)]">
          {label}
        </span>
        <span className="text-[11px] text-[var(--text-muted)]">{detail}</span>
      </div>
      <span className="ml-auto font-mono text-xs tabular-nums text-[var(--text-secondary)]">
        {formatTokens(tokens)}
      </span>
    </div>
  );
}

export function CostCard({
  summary,
  isLoading = false,
  isError = false,
  restricted = false,
}: CostCardProps) {
  const t = useTranslations("delivery");
  // 권한 없음 — 에러 대신 안내.
  if (restricted) {
    return (
      <CardFrame>
        <div className="flex flex-col items-center gap-2 p-6 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--bg-hover)]">
            <Lock className="h-5 w-5 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-xs font-medium text-[var(--text-secondary)]">
            {t("cost.restrictedTitle")}
          </p>
          <p className="text-[11px] text-[var(--text-muted)]">
            {t.rich("cost.restrictedDesc", {
              b: (chunks) => <b className="font-semibold">{chunks}</b>,
            })}
          </p>
        </div>
      </CardFrame>
    );
  }

  // 로딩 — 스켈레톤.
  if (isLoading) {
    return (
      <CardFrame>
        <div className="flex animate-pulse flex-col gap-4 p-4">
          <div className="flex flex-col gap-1.5">
            <div className="h-2.5 w-24 rounded bg-[var(--bg-hover)]" />
            <div className="h-6 w-32 rounded bg-[var(--bg-hover)]" />
          </div>
          <div className="flex flex-col gap-2.5">
            <div className="h-8 rounded bg-[var(--bg-hover)]" />
            <div className="h-8 rounded bg-[var(--bg-hover)]" />
          </div>
        </div>
      </CardFrame>
    );
  }

  // 에러 — 인라인.
  if (isError) {
    return (
      <CardFrame>
        <div className="m-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {t("cost.errorLoad")}
        </div>
      </CardFrame>
    );
  }

  const totalTokens =
    (summary?.total_input_tokens ?? 0) + (summary?.total_output_tokens ?? 0);
  const rows = summary?.by_key_source ?? [];
  const isEmpty = !summary || (totalTokens === 0 && rows.length === 0);

  // 데이터 없음 — 빈 상태.
  if (isEmpty) {
    return (
      <CardFrame>
        <div className="flex flex-col items-center gap-2 p-6 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--bg-hover)]">
            <Coins className="h-5 w-5 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-xs font-medium text-[var(--text-secondary)]">
            {t("cost.emptyTitle")}
          </p>
          <p className="text-[11px] text-[var(--text-muted)]">
            {t("cost.emptyDesc")}
          </p>
        </div>
      </CardFrame>
    );
  }

  const totalCost = formatCost(summary.total_cost);

  return (
    <CardFrame>
      <div className="flex flex-col gap-4 p-4">
        {/* 대표 지표 — 총 토큰 */}
        <div className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            {t("cost.totalTokens")}
          </span>
          <span className="font-mono text-2xl font-bold tabular-nums leading-none text-[var(--text-primary)]">
            {formatTokens(totalTokens)}
          </span>
          <span className="text-[11px] text-[var(--text-muted)]">
            {t("cost.input")}{" "}
            <span className="font-mono tabular-nums">
              {formatTokens(summary.total_input_tokens)}
            </span>{" "}
            · {t("cost.output")}{" "}
            <span className="font-mono tabular-nums">
              {formatTokens(summary.total_output_tokens)}
            </span>
          </span>
        </div>

        {/* 과금 총액 (조직 API 키 사용분) */}
        <div className="flex items-baseline justify-between border-t border-[var(--border-subtle)] pt-3">
          <span className="text-[11px] font-medium text-[var(--text-muted)]">
            {t("cost.meteredTotal")}
          </span>
          <span className="font-mono text-sm font-semibold tabular-nums text-[var(--text-primary)]">
            {totalCost ?? t("cost.unknown")}
          </span>
        </div>

        {/* key_source 분해 */}
        {rows.length > 0 && (
          <div className="flex flex-col gap-2.5">
            {rows.map((row) => (
              <KeySourceRow key={row.key_source} row={row} />
            ))}
          </div>
        )}

        <p className="border-t border-[var(--border-subtle)] pt-3 text-[11.5px] leading-relaxed text-[var(--text-muted)]">
          {t.rich("cost.footer", {
            b: (chunks) => (
              <b className="font-semibold text-[var(--text-secondary)]">{chunks}</b>
            ),
          })}
        </p>
      </div>
    </CardFrame>
  );
}
