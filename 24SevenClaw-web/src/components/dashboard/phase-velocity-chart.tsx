"use client";

import type { PhaseDuration } from "@/lib/api-client";

const PHASE_LABELS: Record<string, string> = {
  requested: "요청",
  decomposed: "분해",
  assigned: "배정",
  drafting: "초안 작성",
  reviewing: "검토",
  revising: "수정",
  approved: "승인",
  in_development: "개발",
  validated: "검증",
  released: "배포",
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}초`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}분`;
  return `${(seconds / 3600).toFixed(1)}시간`;
}

interface PhaseVelocityChartProps {
  data: PhaseDuration[];
}

export function PhaseVelocityChart({ data }: PhaseVelocityChartProps) {
  const maxDuration = Math.max(...data.map((d) => d.avg_duration_seconds), 1);

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
      <h3 className="mb-1 text-sm font-semibold text-slate-200">
        단계별 평균 소요시간
      </h3>
      <p className="mb-4 text-xs text-slate-500">
        각 파이프라인 단계의 평균 처리 시간
      </p>

      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">
          아직 단계 데이터가 없습니다
        </p>
      ) : (
        <div className="space-y-3">
          {data.map((item) => {
            const label = PHASE_LABELS[item.phase] ?? item.phase;
            const pct = (item.avg_duration_seconds / maxDuration) * 100;

            return (
              <div key={item.phase} className="flex items-center gap-3">
                <span className="w-16 shrink-0 text-right text-xs text-slate-400">
                  {label}
                </span>
                <div className="relative h-6 flex-1 overflow-hidden rounded-lg bg-white/5">
                  <div
                    className="absolute inset-y-0 left-0 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500"
                    style={{
                      width: `${pct}%`,
                      minWidth: item.avg_duration_seconds > 0 ? "8px" : "0",
                    }}
                  />
                </div>
                <span className="w-16 text-right text-xs font-medium text-slate-300">
                  {formatDuration(item.avg_duration_seconds)}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {data.length > 0 && (
        <div className="mt-4 border-t border-white/5 pt-3 text-right text-xs text-slate-500">
          총 {data.reduce((s, d) => s + d.sample_count, 0)}건 샘플
        </div>
      )}
    </div>
  );
}
