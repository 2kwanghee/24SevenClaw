"use client";

import { Clock, Zap } from "lucide-react";

import type { PhaseDuration } from "@/lib/api-client";

/** 기존 수동 개발 대비 ClickEye 자동화 시간을 비교하는 단순 추정 계수 */
const MANUAL_MULTIPLIER = 3.5;

interface ValueComparisonProps {
  avgPhaseDuration: PhaseDuration[];
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}초`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}분`;
  return `${(seconds / 3600).toFixed(1)}시간`;
}

export function ValueComparison({ avgPhaseDuration }: ValueComparisonProps) {
  const totalAutomated = avgPhaseDuration.reduce(
    (sum, p) => sum + p.avg_duration_seconds,
    0,
  );
  const totalManual = totalAutomated * MANUAL_MULTIPLIER;
  const savedPercent =
    totalManual > 0
      ? Math.round(((totalManual - totalAutomated) / totalManual) * 100)
      : 0;

  const maxTime = Math.max(totalManual, totalAutomated, 1);

  return (
    <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
      <h3 className="mb-1 text-sm font-semibold text-[var(--text-primary)]">
        시간 절감 비교
      </h3>
      <p className="mb-6 text-xs text-[var(--text-muted)]">
        기존 수동 개발 대비 ClickEye 자동화 소요시간
      </p>

      <div className="space-y-5">
        {/* 기존 방식 */}
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
              <Clock className="h-3.5 w-3.5" />
              기존 수동
            </span>
            <span className="font-medium text-[var(--text-primary)]">
              {formatDuration(totalManual)}
            </span>
          </div>
          <div className="h-8 overflow-hidden rounded-lg bg-zinc-100">
            <div
              className="h-full rounded-lg bg-zinc-400 transition-all duration-700"
              style={{ width: `${(totalManual / maxTime) * 100}%` }}
            />
          </div>
        </div>

        {/* 24Seven */}
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-violet-600">
              <Zap className="h-3.5 w-3.5" />
              ClickEye 자동화
            </span>
            <span className="font-medium text-violet-600">
              {formatDuration(totalAutomated)}
            </span>
          </div>
          <div className="h-8 overflow-hidden rounded-lg bg-zinc-100">
            <div
              className="h-full rounded-lg bg-gradient-to-r from-violet-500 to-purple-500 transition-all duration-700"
              style={{ width: `${(totalAutomated / maxTime) * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-center gap-2 rounded-xl bg-emerald-50 py-3">
        <Zap className="h-4 w-4 text-emerald-700" />
        <span className="text-sm font-semibold text-emerald-700">
          {savedPercent}% 시간 절감
        </span>
      </div>
    </div>
  );
}
