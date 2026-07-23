"use client";

import { useTranslations } from "next-intl";
import { Clock } from "lucide-react";

import type { PhaseTimelineEntry } from "@/lib/api-client";

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}초`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}분`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  return mins > 0 ? `${hours}시간 ${mins}분` : `${hours}시간`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface ProjectTimelineProps {
  data: PhaseTimelineEntry[];
}

export function ProjectTimeline({ data }: ProjectTimelineProps) {
  const t = useTranslations("delivery.phase");
  return (
    <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
      <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">
        프로젝트 타임라인
      </h3>

      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--text-muted)]">
          아직 단계 이력이 없습니다
        </p>
      ) : (
        <div className="relative space-y-0">
          {data.map((entry, i) => {
            const isLast = i === data.length - 1;
            const label = t.has(entry.phase) ? t(entry.phase) : entry.phase;

            return (
              <div key={`${entry.phase}-${i}`} className="flex gap-3">
                {/* 타임라인 도트 + 라인 */}
                <div className="flex flex-col items-center">
                  <div
                    className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${
                      isLast
                        ? "bg-[var(--accent)] shadow-sm"
                        : "bg-[var(--border-medium)]"
                    }`}
                  />
                  {!isLast && (
                    <div className="w-px flex-1 bg-[var(--border-subtle)]" />
                  )}
                </div>

                {/* 내용 */}
                <div className={`pb-4 ${isLast ? "" : ""}`}>
                  <p className="text-sm font-medium text-[var(--text-primary)]">
                    {label}
                  </p>
                  <div className="mt-0.5 flex items-center gap-2 text-xs text-[var(--text-muted)]">
                    <Clock className="h-3 w-3" />
                    <span>{formatTime(entry.entered_at)}</span>
                    {entry.duration_seconds != null && (
                      <span className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[var(--text-secondary)]">
                        {formatDuration(entry.duration_seconds)}
                      </span>
                    )}
                  </div>
                  {entry.message && (
                    <p className="mt-1 text-xs text-[var(--text-muted)] line-clamp-2">
                      {entry.message}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
