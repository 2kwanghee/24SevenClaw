"use client";

import { useMemo, useState } from "react";

import { AlertCircle, LayoutDashboard } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { RoleGuard } from "@/components/common/role-guard";
import { DeliveryBoard } from "@/components/dashboard/delivery-board";
import { BentoCard, BentoGrid } from "@/components/ui/bento";
import {
  useObservabilitySummary,
  useProjectSummary,
  useSeats,
} from "@/hooks/use-observability";
import { useProjects } from "@/hooks/use-projects";
import {
  ApiClientError,
  type ObservabilityDailyOutcome,
  type ProjectResponse,
  type SeatObservabilityEntry,
} from "@/lib/api-client";
import { cn } from "@/lib/utils";

const PERIOD_PRESETS = [7, 14, 30] as const;

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

/** 실존 상태값(project: active/archived/deleted, intake: pending_review/accepted/rejected) → 색.
 * 알려지지 않은 상태값은 muted 로 안전 폴백한다. */
const STATUS_COLORS: Record<string, string> = {
  active: "var(--accent)",
  archived: "var(--text-muted)",
  deleted: "var(--chart-danger)",
  pending_review: "var(--chart-warning)",
  accepted: "var(--chart-info)",
  rejected: "var(--text-muted)",
};

const KNOWN_STATUS_KEYS = new Set(Object.keys(STATUS_COLORS));

function colorFor(key: string): string {
  return STATUS_COLORS[key] ?? "var(--text-muted)";
}

/** 상태 라벨 i18n — 실존 6개 상태값만 번역 커버, 미지 값은 원래 key로 폴백 */
function statusLabel(
  t: ReturnType<typeof useTranslations>,
  key: string,
): string {
  return KNOWN_STATUS_KEYS.has(key) ? t(`status.${key}`) : key;
}

interface StatusTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { key: string; value: number; pct: number } }>;
  t: ReturnType<typeof useTranslations>;
}

function StatusTooltip({ active, payload, t }: StatusTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const { key, value, pct } = payload[0].payload;
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-[var(--text-primary)]">
        {statusLabel(t, key)}
      </p>
      <p className="tabular-nums text-[var(--text-secondary)]">
        {value} ({pct}%)
      </p>
    </div>
  );
}

/** 프로젝트 개별 상세(hover) — 토큰 합계·활동 기간·사용 계정 목록. CE-402 summary API 소비. */
function ProjectDetailCard({ projectId }: { projectId: string }) {
  const t = useTranslations("observability.dashboard.projectDetail");
  const { data, isLoading, error } = useProjectSummary(projectId, true);

  if (isLoading) {
    return <p className="text-xs text-[var(--text-muted)]">{t("loading")}</p>;
  }
  if (error || !data) {
    return <p className="text-xs text-[var(--text-muted)]">{t("error")}</p>;
  }

  const accounts = data.seats
    .map((s) => s.account_email)
    .filter((email): email is string => !!email);

  return (
    <div className="mt-2 space-y-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-2.5 text-xs">
      <p className="text-[var(--text-secondary)]">
        {t("tokens")}:{" "}
        <span className="tabular-nums font-medium text-[var(--text-primary)]">
          {data.total_input_tokens + data.total_output_tokens}
        </span>
      </p>
      <p className="text-[var(--text-secondary)]">
        {t("period")}:{" "}
        <span className="text-[var(--text-primary)]">
          {data.first_activity_at
            ? new Date(data.first_activity_at).toLocaleDateString("ko-KR")
            : "—"}
          {" ~ "}
          {data.last_activity_at
            ? new Date(data.last_activity_at).toLocaleDateString("ko-KR")
            : "—"}
        </span>
      </p>
      <p className="text-[var(--text-secondary)]">
        {t("accounts")}:{" "}
        <span className="text-[var(--text-primary)]">
          {accounts.length > 0 ? accounts.join(", ") : t("accountsPending")}
        </span>
      </p>
    </div>
  );
}

/** 상태별 프로젝트 목록(클릭 시 펼침) + 항목 hover 시 상세 카드.
 * projects_by_status 는 상태별 합계값만 가지고 있어 project_id 를 포함하지 않으므로,
 * 이미 존재하는 useProjects() 목록(id 포함)과 클라이언트에서 상태로 매칭해 사용한다(신규 API 없음).
 * deleted 상태는 프로젝트 목록 API 가 반환하지 않아(soft-delete 제외) 매칭 불가 — noList 안내로 폴백. */
function ProjectStatusList({
  statusKey,
  projects,
  isLoading,
}: {
  statusKey: string;
  projects: ProjectResponse[] | undefined;
  isLoading: boolean;
}) {
  const t = useTranslations("observability.dashboard.projectDetail");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const matched = (projects ?? []).filter((p) => p.status === statusKey);

  if (isLoading) {
    return <p className="mt-2 text-xs text-[var(--text-muted)]">{t("loading")}</p>;
  }

  if (matched.length === 0) {
    return <p className="mt-2 text-xs text-[var(--text-muted)]">{t("noList")}</p>;
  }

  return (
    <div className="mt-2 space-y-1">
      {matched.map((p) => (
        <div key={p.id}>
          <button
            type="button"
            onMouseEnter={() => setHoveredId(p.id)}
            onMouseLeave={() => setHoveredId((cur) => (cur === p.id ? null : cur))}
            onFocus={() => setHoveredId(p.id)}
            className="w-full rounded-md px-2 py-1 text-left text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
          >
            {p.name}
          </button>
          {hoveredId === p.id && <ProjectDetailCard projectId={p.id} />}
        </div>
      ))}
    </div>
  );
}

function StatusBarChart({
  data,
  emptyLabel,
  interactive,
  allProjects,
  projectsLoading,
}: {
  data: Record<string, number>;
  emptyLabel: string;
  interactive?: boolean;
  allProjects?: ProjectResponse[];
  projectsLoading?: boolean;
}) {
  const t = useTranslations("observability.dashboard");
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const entries = Object.entries(data);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  const chartData = useMemo(
    () =>
      entries.map(([key, value]) => ({
        key,
        value,
        pct: total > 0 ? Math.round((value / total) * 100) : 0,
      })),
    [entries, total],
  );

  if (entries.length === 0 || total === 0) {
    return <p className="text-sm text-[var(--text-muted)]">{emptyLabel}</p>;
  }

  return (
    <div className="mt-4">
      <ResponsiveContainer width="100%" height={chartData.length * 44 + 16}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 32, left: 0, bottom: 4 }}
        >
          <XAxis type="number" hide domain={[0, total]} />
          <YAxis
            type="category"
            dataKey="key"
            width={92}
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 14, fill: "var(--text-secondary)" }}
            tickFormatter={(key: string) => statusLabel(t, key)}
          />
          <Tooltip
            content={<StatusTooltip t={t} />}
            cursor={{ fill: "var(--bg-hover)" }}
          />
          <Bar
            dataKey="value"
            radius={[4, 4, 4, 4]}
            barSize={18}
            isAnimationActive
            animationDuration={500}
            onClick={(entry: unknown) => {
              const key = (entry as { payload?: { key?: string } } | undefined)?.payload
                ?.key;
              if (!interactive || !key) return;
              setSelectedStatus((cur) => (cur === key ? null : key));
            }}
            cursor={interactive ? "pointer" : undefined}
          >
            {chartData.map((entry) => (
              <Cell key={entry.key} fill={colorFor(entry.key)} />
            ))}
            <LabelList
              dataKey="value"
              position="right"
              style={{
                fill: "var(--text-muted)",
                fontSize: 14,
                fontWeight: 600,
              }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {interactive && (
        <>
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            {t("projectDetail.hint")}
          </p>
          {selectedStatus && (
            <ProjectStatusList
              statusKey={selectedStatus}
              projects={allProjects}
              isLoading={!!projectsLoading}
            />
          )}
        </>
      )}
    </div>
  );
}

function PeriodSelector({
  days,
  onChange,
}: {
  days: number;
  onChange: (days: number) => void;
}) {
  const t = useTranslations("observability.dashboard");

  return (
    <div
      role="group"
      aria-label={t("periodLabel")}
      className="flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-0.5"
    >
      {PERIOD_PRESETS.map((preset) => (
        <button
          key={preset}
          type="button"
          onClick={() => onChange(preset)}
          aria-pressed={days === preset}
          className={cn(
            "rounded-md px-2 py-1 text-xs font-medium transition-colors",
            days === preset
              ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm"
              : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]",
          )}
        >
          {t(`days${preset}` as "days7" | "days14" | "days30")}
        </button>
      ))}
    </div>
  );
}

function SuccessRatePie({
  rate,
  successCount,
  failureCount,
  days,
}: {
  rate: number | null;
  successCount: number;
  failureCount: number;
  days: number;
}) {
  const t = useTranslations("observability.dashboard");
  const pct = rate !== null ? Math.round(rate * 100) : null;

  if (pct === null && successCount === 0 && failureCount === 0) {
    return (
      <p className="text-xs text-[var(--text-muted)]">{t("noRuns", { days })}</p>
    );
  }

  const displayPct = pct ?? 0;
  const pieData = [
    { key: "success", value: successCount, fill: "var(--accent)" },
    { key: "failure", value: failureCount, fill: "var(--chart-danger)" },
  ];

  return (
    <div className="mt-4 flex items-center gap-5">
      <div
        className="relative h-24 w-24 shrink-0"
        role="img"
        aria-label={t("successRateAria", { pct: displayPct })}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="key"
              innerRadius="70%"
              outerRadius="100%"
              startAngle={90}
              endAngle={-270}
              isAnimationActive
              animationDuration={500}
              stroke="none"
            >
              {pieData.map((entry) => (
                <Cell key={entry.key} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-semibold tabular-nums text-[var(--text-primary)]">
            {pct !== null ? `${pct}%` : "—"}
          </span>
        </div>
      </div>
      <div className="space-y-1 text-xs">
        <p className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[var(--accent)]" />
          <span className="text-[var(--text-secondary)]">
            {t("success")}: <span className="tabular-nums">{successCount}</span>
          </span>
        </p>
        <p className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[var(--chart-danger)]" />
          <span className="text-[var(--text-secondary)]">
            {t("failure")}: <span className="tabular-nums">{failureCount}</span>
          </span>
        </p>
      </div>
    </div>
  );
}

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

interface DailyTrendTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: { date: string; success: number; failure: number };
  }>;
}

function DailyTrendTooltip({ active, payload }: DailyTrendTooltipProps) {
  const t = useTranslations("observability.dashboard");
  if (!active || !payload || payload.length === 0) return null;
  const { date, success, failure } = payload[0].payload;
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-[var(--text-primary)]">
        {new Date(date).toLocaleDateString("ko-KR", {
          month: "numeric",
          day: "numeric",
        })}
      </p>
      <p className="tabular-nums text-[var(--text-secondary)]">
        {t("success")}: {success} · {t("failure")}: {failure}
      </p>
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

function DailyOutcomeTrend({ data }: { data: ObservabilityDailyOutcome[] }) {
  const t = useTranslations("observability.dashboard");
  const isEmpty = data.every((d) => d.success === 0 && d.failure === 0);

  return (
    <div className="mt-4 flex-1">
      <p className="mb-2 text-xs font-medium text-[var(--text-secondary)]">
        {t("recentTrend")}
      </p>
      {isEmpty ? (
        <p className="text-xs text-[var(--text-muted)]">{t("trendEmpty")}</p>
      ) : (
        <ResponsiveContainer width="100%" height={120}>
          <BarChart
            data={data}
            margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
          >
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "var(--text-muted)" }}
              tickFormatter={(d: string) =>
                new Date(d).toLocaleDateString("ko-KR", {
                  month: "numeric",
                  day: "numeric",
                })
              }
            />
            <YAxis hide />
            <Tooltip content={<DailyTrendTooltip />} cursor={{ fill: "var(--bg-hover)" }} />
            <Bar
              dataKey="success"
              stackId="outcome"
              fill="var(--accent)"
              radius={[0, 0, 0, 0]}
              isAnimationActive
              animationDuration={500}
            />
            <Bar
              dataKey="failure"
              stackId="outcome"
              fill="var(--chart-danger)"
              radius={[4, 4, 0, 0]}
              isAnimationActive
              animationDuration={500}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function DashboardContent() {
  const t = useTranslations("observability.dashboard");
  const [days, setDays] = useState(7);
  const { data, isLoading, error } = useObservabilitySummary(days);
  // projects_by_status 는 상태별 합계만 제공(project_id 미포함) → hover 상세 목록을 위해
  // 이미 존재하는 프로젝트 목록(id 포함) API 를 함께 조회해 클라이언트에서 상태로 매칭한다.
  const { data: projectsData, isLoading: projectsLoading } = useProjects({
    limit: 100,
  });
  // CE-405: 계정 잔량/사용순위 위젯 — 기존 GET /observability/seats 재사용, 요약 데이터와 독립 로딩.
  const { data: seatsData, isLoading: seatsLoading, error: seatsError } = useSeats();

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

      <DeliveryBoard />

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
        <BentoGrid className="lg:grid-cols-2">
          <BentoCard title={t("projectsByStatus")}>
            <StatusBarChart
              data={data.projects_by_status}
              emptyLabel={t("empty")}
              interactive
              allProjects={projectsData?.items}
              projectsLoading={projectsLoading}
            />
          </BentoCard>

          <BentoCard title={t("intakeFunnel")}>
            <StatusBarChart data={data.intake_by_status} emptyLabel={t("empty")} />
          </BentoCard>

          <BentoCard
            size="lg"
            title={t("pipelineSuccessRate", { days })}
            action={<PeriodSelector days={days} onChange={setDays} />}
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <SuccessRatePie
                rate={data.pipeline_run_success_rate}
                successCount={data.pipeline_run_success_count}
                failureCount={data.pipeline_run_failure_count}
                days={days}
              />
              <DailyOutcomeTrend data={data.daily_outcomes} />
            </div>
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

          <BentoCard title={t("seatBalance.title")} href="/observability/seats">
            {seatsLoading ? (
              <p className="mt-4 text-xs text-[var(--text-muted)]">{t("loading")}</p>
            ) : seatsError ? (
              <p className="mt-4 text-xs text-[var(--text-muted)]">{t("error")}</p>
            ) : (
              <SeatBalanceGauges items={seatsData?.items ?? []} />
            )}
          </BentoCard>

          <BentoCard size="wide" title={t("seatRanking.title")} href="/observability/seats">
            {seatsLoading ? (
              <p className="mt-4 text-xs text-[var(--text-muted)]">{t("loading")}</p>
            ) : seatsError ? (
              <p className="mt-4 text-xs text-[var(--text-muted)]">{t("error")}</p>
            ) : (
              <SeatRankingTable items={seatsData?.items ?? []} />
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
