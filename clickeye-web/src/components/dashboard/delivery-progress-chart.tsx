"use client";

import { useMemo } from "react";

import { useTranslations } from "next-intl";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useDeliveryBoard } from "@/hooks/use-observability";
import { ApiClientError } from "@/lib/api-client";

import {
  COLUMN_COLORS,
  DANGER_COLOR,
  isDangerTicket,
  resolveTicketColumn,
  STAGE_COLUMNS,
  type StageColumnKey,
} from "./delivery-board-constants";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

interface ProgressBar {
  key: StageColumnKey;
  label: string;
  normal: number;
  danger: number;
  total: number;
}

interface ProgressTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: ProgressBar }>;
  t: ReturnType<typeof useTranslations>;
}

function ProgressTooltip({ active, payload, t }: ProgressTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const { label, danger, total } = payload[0].payload;
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-[var(--text-primary)]">{label}</p>
      <p className="tabular-nums text-[var(--text-secondary)]">
        {t("progress.ticketCount", { count: total })}
        {danger > 0 && (
          <span className="text-[var(--chart-danger)]">
            {" "}
            ({t("progress.failed")} {danger})
          </span>
        )}
      </p>
    </div>
  );
}

function StatTile({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="flex flex-col rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2">
      <span className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
        {label}
      </span>
      <span className="mt-0.5 text-xl font-semibold tabular-nums text-[var(--text-primary)]">
        {value}
      </span>
    </div>
  );
}

/**
 * 딜리버리 진행 현황 — useDeliveryBoard() 데이터로 8단계별 티켓 수를 스택 바로,
 * 상단에 진행중/완료/실패 요약 스탯을 렌더한다. 구 "파이프라인 성공률" 위젯 대체(CE-412 후속).
 * 단계 매핑·색·danger 판정은 delivery-board-constants 를 그대로 재사용한다.
 */
export function DeliveryProgressChart() {
  const t = useTranslations("observability.dashboard");
  const tBoard = useTranslations("observability.dashboard.deliveryBoard");
  const { data, isLoading, error } = useDeliveryBoard();

  const { chartData, inProgress, done, failed, total } = useMemo(() => {
    const counts = STAGE_COLUMNS.reduce<
      Record<StageColumnKey, { normal: number; danger: number }>
    >(
      (acc, col) => {
        acc[col] = { normal: 0, danger: 0 };
        return acc;
      },
      {} as Record<StageColumnKey, { normal: number; danger: number }>,
    );

    let inProgress = 0;
    let done = 0;
    let failed = 0;

    for (const project of data?.projects ?? []) {
      for (const ticket of project.tickets ?? []) {
        const col = resolveTicketColumn(ticket);
        const danger = isDangerTicket(ticket, project.intake_status);
        if (danger) {
          counts[col].danger += 1;
          failed += 1;
        } else {
          counts[col].normal += 1;
          if (col === "done") done += 1;
          else inProgress += 1;
        }
      }
    }

    const chartData: ProgressBar[] = STAGE_COLUMNS.map((col) => ({
      key: col,
      label: tBoard(`columns.${col}`),
      normal: counts[col].normal,
      danger: counts[col].danger,
      total: counts[col].normal + counts[col].danger,
    }));

    return {
      chartData,
      inProgress,
      done,
      failed,
      total: inProgress + done + failed,
    };
  }, [data, tBoard]);

  if (isLoading) {
    return <p className="text-sm text-[var(--text-muted)]">{t("loading")}</p>;
  }

  if (error && isFeatureDisabled(error)) {
    return <p className="text-sm text-[var(--text-muted)]">{t("featureDisabled")}</p>;
  }

  if (error) {
    return <p className="text-sm text-[var(--chart-danger)]">{t("error")}</p>;
  }

  if (total === 0) {
    return <p className="text-sm text-[var(--text-muted)]">{t("progress.empty")}</p>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <StatTile label={t("progress.inProgress")} value={inProgress} color="var(--accent)" />
        <StatTile label={t("progress.done")} value={done} color="var(--chart-info)" />
        <StatTile label={t("progress.failed")} value={failed} color={DANGER_COLOR} />
      </div>

      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={chartData} margin={{ top: 16, right: 4, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            interval={0}
            tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
          />
          <YAxis hide />
          <Tooltip content={<ProgressTooltip t={t} />} cursor={{ fill: "var(--bg-hover)" }} />
          <Bar dataKey="normal" stackId="stage" isAnimationActive animationDuration={500}>
            {chartData.map((entry) => (
              <Cell key={entry.key} fill={COLUMN_COLORS[entry.key]} />
            ))}
          </Bar>
          <Bar
            dataKey="danger"
            stackId="stage"
            fill={DANGER_COLOR}
            radius={[4, 4, 0, 0]}
            isAnimationActive
            animationDuration={500}
          >
            <LabelList
              dataKey="total"
              position="top"
              formatter={(value) => {
                const n = typeof value === "number" ? value : Number(value);
                return n > 0 ? n : "";
              }}
              style={{ fill: "var(--text-muted)", fontSize: 12, fontWeight: 600 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
