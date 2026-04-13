"use client";

import type { ArtifactStatusCount } from "@/lib/api-client";

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: "초안", color: "bg-slate-500" },
  reviewed: { label: "검토됨", color: "bg-blue-500" },
  revised: { label: "수정됨", color: "bg-amber-500" },
  approved: { label: "승인됨", color: "bg-emerald-500" },
  in_development: { label: "개발 중", color: "bg-violet-500" },
  validated: { label: "검증됨", color: "bg-cyan-500" },
  released: { label: "배포됨", color: "bg-green-400" },
};

interface ArtifactStatusChartProps {
  data: ArtifactStatusCount[];
}

export function ArtifactStatusChart({ data }: ArtifactStatusChartProps) {
  const total = data.reduce((sum, d) => sum + d.count, 0);
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
      <h3 className="mb-4 text-sm font-semibold text-slate-200">
        산출물 상태별 현황
      </h3>

      {total === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">
          아직 산출물이 없습니다
        </p>
      ) : (
        <div className="space-y-3">
          {data.map((item) => {
            const cfg = STATUS_CONFIG[item.status] ?? {
              label: item.status,
              color: "bg-slate-600",
            };
            const pct = (item.count / maxCount) * 100;

            return (
              <div key={item.status} className="flex items-center gap-3">
                <span className="w-20 shrink-0 text-right text-xs text-slate-400">
                  {cfg.label}
                </span>
                <div className="relative h-6 flex-1 overflow-hidden rounded-lg bg-white/5">
                  <div
                    className={`absolute inset-y-0 left-0 rounded-lg transition-all duration-500 ${cfg.color}`}
                    style={{ width: `${pct}%`, minWidth: item.count > 0 ? "8px" : "0" }}
                  />
                </div>
                <span className="w-8 text-right text-xs font-medium text-slate-300">
                  {item.count}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 border-t border-white/5 pt-3 text-right text-xs text-slate-500">
        총 {total}개 산출물
      </div>
    </div>
  );
}
