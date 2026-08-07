"use client";

import { useTranslations } from "next-intl";
import {
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
} from "recharts";

import { type SeatObservabilityEntry } from "@/lib/api-client";

// CE-418: page.tsx 의 named export 는 Next App Router 예약 export 검사(tsc)에 걸리므로
// 대시보드 계정 위젯 2종을 여기로 추출했다. 동작·마크업 무변경.

/** 리셋까지 남은 시간 — 일/시간 단위 조각(초 단위 실시간 갱신 없음). resets_at 파싱 실패 시 null. */
function formatRemaining(resetsAt: string): { days: number; hours: number } | null {
  const diffMs = new Date(resetsAt).getTime() - Date.now();
  if (Number.isNaN(diffMs) || diffMs <= 0) return { days: 0, hours: 0 };
  const totalHours = Math.floor(diffMs / (1000 * 60 * 60));
  return { days: Math.floor(totalHours / 24), hours: totalHours % 24 };
}

/** 계정별 잔량 게이지 — 5h/7d 비스코프 윈도우는 라디얼 게이지, 모델 스코프 윈도우는 선형 바.
 * CE-405: GET /observability/seats(기존, 무변경)만 소비. */
export function SeatBalanceGauges({ items }: { items: SeatObservabilityEntry[] }) {
  const t = useTranslations("observability.dashboard");

  if (items.length === 0) {
    return <p className="mt-4 text-xs text-[var(--text-muted)]">{t("seatBalance.empty")}</p>;
  }

  return (
    <div className="mt-4 space-y-4">
      {items.map((entry) => {
        const primaryWindows = entry.windows.filter(
          (w) => (w.window === "5h" || w.window === "7d") && w.scope_name === null,
        );
        const scopedWindows = entry.windows.filter((w) => w.scope_name !== null);
        const resetWindow =
          entry.windows.find((w) => w.window === "7d" && w.resets_at) ??
          entry.windows.find((w) => w.resets_at);
        const riskWindow = entry.windows.find(
          (w) => w.projected_exhaustion_at && w.will_last_to_reset === false,
        );

        return (
          <div
            key={entry.account_email}
            className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-[var(--text-primary)]">
                {entry.account_email}
              </p>
              {riskWindow && (
                <span
                  className="rounded-full border px-2 py-0.5 text-xs"
                  style={{ borderColor: "var(--chart-danger)", color: "var(--chart-danger)" }}
                >
                  {t("seatBalance.exhaustionRisk")}
                </span>
              )}
            </div>

            <div className="mt-3 flex flex-wrap gap-4">
              {primaryWindows.map((w) => {
                const pct = Math.min(100, Math.max(0, Number(w.pct) || 0));
                return (
                  <div key={w.window} className="relative h-20 w-20">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadialBarChart
                        innerRadius="70%"
                        outerRadius="100%"
                        barSize={8}
                        data={[{ pct }]}
                        startAngle={90}
                        endAngle={-270}
                      >
                        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                        <RadialBar
                          dataKey="pct"
                          fill="var(--accent)"
                          background={{ fill: "var(--bg-hover)" }}
                          cornerRadius={4}
                        />
                      </RadialBarChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-xs font-semibold tabular-nums text-[var(--text-primary)]">
                        {pct}%
                      </span>
                      <span className="text-[10px] text-[var(--text-muted)]">{w.window}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {scopedWindows.length > 0 && (
              <div className="mt-3 space-y-1.5">
                {scopedWindows.map((w) => {
                  const pct = Math.min(100, Math.max(0, Number(w.pct) || 0));
                  const color =
                    pct >= 90
                      ? "var(--chart-danger)"
                      : pct >= 70
                        ? "var(--chart-warning)"
                        : "var(--chart-info)";
                  return (
                    <div key={`${w.window}-${w.scope_name}`} className="text-xs">
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-[var(--text-secondary)]">{w.scope_name}</span>
                        <span className="tabular-nums text-[var(--text-muted)]">{pct}%</span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--bg-hover)]">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, backgroundColor: color }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {resetWindow?.resets_at &&
              (() => {
                const remaining = formatRemaining(resetWindow.resets_at);
                if (!remaining) return null;
                const value =
                  remaining.days > 0
                    ? `${remaining.days}${t("seatBalance.unitDay")} ${remaining.hours}${t("seatBalance.unitHour")}`
                    : `${remaining.hours}${t("seatBalance.unitHour")}`;
                return (
                  <p className="mt-2 text-[10px] text-[var(--text-muted)]">
                    {t("seatBalance.resetsIn", { value })}
                  </p>
                );
              })()}
          </div>
        );
      })}
    </div>
  );
}

/** 계정 사용 순위(24h) — 24h input+output 합산 내림차순. "last used" 컬럼은 스펙상 범위 외. */
export function SeatRankingTable({ items }: { items: SeatObservabilityEntry[] }) {
  const t = useTranslations("observability.dashboard");

  if (items.length === 0) {
    return <p className="mt-4 text-xs text-[var(--text-muted)]">{t("seatRanking.empty")}</p>;
  }

  const sorted = [...items].sort(
    (a, b) =>
      b.usage_24h_input_tokens +
      b.usage_24h_output_tokens -
      (a.usage_24h_input_tokens + a.usage_24h_output_tokens),
  );

  return (
    <table className="mt-4 w-full text-sm">
      <thead>
        <tr className="border-b border-[var(--border-subtle)] text-left text-xs text-[var(--text-muted)]">
          <th className="py-1.5 pr-2 font-medium">{t("seatRanking.rank")}</th>
          <th className="py-1.5 pr-2 font-medium">{t("seatRanking.account")}</th>
          <th className="py-1.5 pr-2 text-right font-medium">{t("seatRanking.usage24h")}</th>
          <th className="py-1.5 text-right font-medium">{t("seatRanking.balance")}</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((entry, idx) => {
          const usage = entry.usage_24h_input_tokens + entry.usage_24h_output_tokens;
          const balanceWindow = entry.windows.find(
            (w) => w.window === "7d" && w.scope_name === null,
          );
          const balance = balanceWindow
            ? `${Math.round(Number(balanceWindow.pct) || 0)}%`
            : "—";
          return (
            <tr
              key={entry.account_email}
              className="border-b border-[var(--border-subtle)] last:border-b-0"
            >
              <td className="py-1.5 pr-2 tabular-nums text-[var(--text-muted)]">{idx + 1}</td>
              <td className="py-1.5 pr-2 text-[var(--text-secondary)]">
                {entry.account_email}
              </td>
              <td className="py-1.5 pr-2 text-right tabular-nums text-[var(--text-primary)]">
                {usage}
              </td>
              <td className="py-1.5 text-right tabular-nums text-[var(--text-primary)]">
                {balance}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
