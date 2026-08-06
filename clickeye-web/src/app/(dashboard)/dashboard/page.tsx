"use client";

import { useMemo, useState } from "react";

import { AlertCircle, LayoutDashboard } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { RoleGuard } from "@/components/common/role-guard";
import { BentoCard, BentoGrid } from "@/components/ui/bento";
import {
  useObservabilitySummary,
  useProjectSummary,
  useSeats,
} from "@/hooks/use-observability";
import { useProjects } from "@/hooks/use-projects";
import {
  ApiClientError,
  type ProjectResponse,
  type SeatObservabilityEntry,
} from "@/lib/api-client";

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

/** 리셋까지 남은 시간 — 일/시간 단위 조각(초 단위 실시간 갱신 없음). */
function formatRemaining(resetsAt: string): string {
  const diffMs = new Date(resetsAt).getTime() - Date.now();
  if (diffMs <= 0) return "0h";
  const totalHours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
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

            {resetWindow?.resets_at && (
              <p className="mt-2 text-[10px] text-[var(--text-muted)]">
                {t("seatBalance.resetsIn", { value: formatRemaining(resetWindow.resets_at) })}
              </p>
            )}
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

function DashboardContent() {
  const t = useTranslations("observability.dashboard");
  const { data, isLoading, error } = useObservabilitySummary();
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
