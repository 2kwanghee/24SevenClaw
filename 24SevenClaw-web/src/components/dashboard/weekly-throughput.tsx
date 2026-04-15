"use client";

import { TrendingUp } from "lucide-react";

import type { WeeklyThroughput as WeeklyThroughputType } from "@/lib/api-client";

interface WeeklyThroughputProps {
  data: WeeklyThroughputType[];
}

function formatWeekLabel(weekStart: string): string {
  const d = new Date(weekStart);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export function WeeklyThroughput({ data }: WeeklyThroughputProps) {
  const maxCount = Math.max(...data.map((d) => d.completed_count), 1);
  const total = data.reduce((sum, d) => sum + d.completed_count, 0);

  // SVG 스파크라인 좌표 생성
  const width = 280;
  const height = 60;
  const padding = 4;
  const points = data.map((d, i) => {
    const x =
      data.length > 1
        ? padding + (i / (data.length - 1)) * (width - padding * 2)
        : width / 2;
    const y =
      height - padding - (d.completed_count / maxCount) * (height - padding * 2);
    return { x, y };
  });
  const pathD =
    points.length > 1
      ? points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ")
      : "";
  const areaD =
    points.length > 1
      ? `${pathD} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`
      : "";

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">
            주간 처리량
          </h3>
          <p className="text-xs text-slate-500">주별 완료된 태스크 수</p>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-1">
          <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-xs font-medium text-emerald-300">
            총 {total}건
          </span>
        </div>
      </div>

      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">
          아직 주간 데이터가 없습니다
        </p>
      ) : (
        <>
          {/* 스파크라인 SVG */}
          <div className="flex justify-center">
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="h-16 w-full max-w-[280px]"
              preserveAspectRatio="none"
            >
              {/* 영역 그라디언트 */}
              <defs>
                <linearGradient
                  id="throughput-gradient"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
                </linearGradient>
              </defs>
              {areaD && (
                <path d={areaD} fill="url(#throughput-gradient)" />
              )}
              {pathD && (
                <path
                  d={pathD}
                  fill="none"
                  stroke="#8b5cf6"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}
              {/* 데이터 포인트 */}
              {points.map((p, i) => (
                <circle
                  key={data[i].week_start}
                  cx={p.x}
                  cy={p.y}
                  r="3"
                  fill="#1e1b4b"
                  stroke="#8b5cf6"
                  strokeWidth="1.5"
                />
              ))}
            </svg>
          </div>

          {/* 주 라벨 */}
          <div className="mt-3 flex justify-between px-1">
            {data.map((d) => (
              <div key={d.week_start} className="text-center">
                <p className="text-[10px] text-slate-500">
                  {formatWeekLabel(d.week_start)}
                </p>
                <p className="text-xs font-medium text-slate-400">
                  {d.completed_count}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
