"use client";

import { Clock, Users, Activity, TrendingUp, DollarSign, Wrench } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

/* ── 정량 지표 배지/바 — 카드와 비교표에서 재사용 ── */

interface EstimatedWeeksBadgeProps {
  min?: number | null;
  max?: number | null;
}

export function EstimatedWeeksBadge({ min, max }: EstimatedWeeksBadgeProps) {
  const t = useTranslations("wizard.metricBadges");
  if (min == null && max == null) return null;
  const unit = t("weeksUnit");
  const text = min === max ? `${min}${unit}` : `${min ?? "?"}~${max ?? "?"}${unit}`;
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-700">
      <Clock className="h-3 w-3" />
      {text}
    </span>
  );
}

interface TeamSizeBadgeProps {
  min?: number | null;
  max?: number | null;
  roles?: string[];
}

export function TeamSizeBadge({ min, max, roles }: TeamSizeBadgeProps) {
  const t = useTranslations("wizard.metricBadges");
  if (min == null && max == null) return null;
  const unit = t("personsUnit");
  const size = min === max ? `${min}${unit}` : `${min ?? "?"}~${max ?? "?"}${unit}`;
  const roleText = roles && roles.length > 0 ? ` (${roles.join("/")})` : "";
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-medium text-emerald-700">
      <Users className="h-3 w-3" />
      {size}
      {roleText}
    </span>
  );
}

interface MonthlyCostBadgeProps {
  minUsd?: number | null;
  maxUsd?: number | null;
}

export function MonthlyCostBadge({ minUsd, maxUsd }: MonthlyCostBadgeProps) {
  if (minUsd == null && maxUsd == null) return null;
  const text =
    minUsd === maxUsd ? `$${minUsd}/mo` : `$${minUsd ?? "?"}~${maxUsd ?? "?"}/mo`;
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700">
      <DollarSign className="h-3 w-3" />
      {text}
    </span>
  );
}

interface MaintenanceBadgeProps {
  level?: string | null;
}

export function MaintenanceBadge({ level }: MaintenanceBadgeProps) {
  const t = useTranslations("wizard.metricBadges");
  if (!level) return null;
  const label =
    level === "low"
      ? t("maintenance.low")
      : level === "high"
        ? t("maintenance.high")
        : t("maintenance.medium");
  const color =
    level === "low"
      ? "bg-green-50 text-green-700"
      : level === "high"
        ? "bg-red-50 text-red-700"
        : "bg-zinc-100 text-zinc-700";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium",
        color,
      )}
    >
      <Wrench className="h-3 w-3" />
      {label}
    </span>
  );
}

interface ScoreBarProps {
  /** 표시 라벨 */
  label: string;
  /** 1~10 점수 */
  score?: number | null;
  /** 색상 — 복잡도/확장성 등 의미별 차별 */
  variant?: "complexity" | "scalability";
}

export function ScoreBar({ label, score, variant = "complexity" }: ScoreBarProps) {
  if (score == null) return null;
  const clamped = Math.max(1, Math.min(10, score));
  const percent = clamped * 10;
  const Icon = variant === "complexity" ? Activity : TrendingUp;
  const barColor =
    variant === "complexity"
      ? clamped >= 8
        ? "bg-rose-500"
        : clamped >= 5
          ? "bg-orange-400"
          : "bg-emerald-500"
      : clamped >= 8
        ? "bg-violet-500"
        : clamped >= 5
          ? "bg-sky-500"
          : "bg-zinc-400";
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-3 w-3 shrink-0 text-zinc-500" />
      <span className="w-[60px] shrink-0 text-[11px] text-zinc-600">{label}</span>
      <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
        <div
          className={cn("absolute left-0 top-0 h-full rounded-full", barColor)}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="w-7 shrink-0 text-right text-[11px] font-medium text-zinc-700">
        {clamped}/10
      </span>
    </div>
  );
}

/** 정량 지표가 하나라도 있는지 — 카드에서 섹션 표시 여부 판단 */
export function hasAnyMetric(p: {
  estimatedWeeksMin?: number | null;
  teamSizeMin?: number | null;
  complexityScore?: number | null;
  scalabilityScore?: number | null;
  monthlyCostMinUsd?: number | null;
  maintenanceDifficulty?: string | null;
}): boolean {
  return (
    p.estimatedWeeksMin != null ||
    p.teamSizeMin != null ||
    p.complexityScore != null ||
    p.scalabilityScore != null ||
    p.monthlyCostMinUsd != null ||
    !!p.maintenanceDifficulty
  );
}
