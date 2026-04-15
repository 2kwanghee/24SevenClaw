"use client";

import { Cpu, User } from "lucide-react";

interface AutomationBreakdownProps {
  automationRate: number;
}

export function AutomationBreakdown({ automationRate }: AutomationBreakdownProps) {
  const humanRate = Math.max(100 - automationRate, 0);
  const roundedAuto = Math.round(automationRate);
  const roundedHuman = 100 - roundedAuto;

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
      <h3 className="mb-1 text-sm font-semibold text-slate-200">
        AI vs 사람 작업 비율
      </h3>
      <p className="mb-6 text-xs text-slate-500">
        자동화된 태스크와 수동 태스크 비율
      </p>

      {/* 도넛 차트 (CSS conic-gradient) */}
      <div className="flex items-center justify-center">
        <div className="relative h-40 w-40">
          <div
            className="h-full w-full rounded-full"
            style={{
              background: `conic-gradient(
                #8b5cf6 0deg ${automationRate * 3.6}deg,
                #334155 ${automationRate * 3.6}deg 360deg
              )`,
            }}
          />
          {/* 중심 구멍 */}
          <div className="absolute inset-4 flex flex-col items-center justify-center rounded-full bg-slate-900">
            <span className="text-2xl font-bold text-slate-100">
              {roundedAuto}%
            </span>
            <span className="text-[10px] text-slate-500">자동화</span>
          </div>
        </div>
      </div>

      {/* 범례 */}
      <div className="mt-6 flex justify-center gap-6">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/20">
            <Cpu className="h-3.5 w-3.5 text-violet-400" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-300">AI 자동화</p>
            <p className="text-[10px] text-slate-500">{roundedAuto}%</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-slate-600/20">
            <User className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-300">수동 작업</p>
            <p className="text-[10px] text-slate-500">{roundedHuman}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
