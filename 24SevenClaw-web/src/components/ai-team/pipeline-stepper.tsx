"use client";

import { Check } from "lucide-react";

import type { OrchestratorPhase } from "@/lib/api-client";

const PHASES: { key: OrchestratorPhase; label: string }[] = [
  { key: "requested", label: "요청" },
  { key: "decomposed", label: "분해" },
  { key: "assigned", label: "배정" },
  { key: "drafting", label: "초안" },
  { key: "reviewing", label: "리뷰" },
  { key: "integrating", label: "통합" },
  { key: "validating", label: "검증" },
  { key: "approved", label: "승인" },
  { key: "transitioning", label: "전환" },
  { key: "completed", label: "완료" },
];

interface PipelineStepperProps {
  currentPhase: OrchestratorPhase;
}

export function PipelineStepper({ currentPhase }: PipelineStepperProps) {
  const currentIndex = PHASES.findIndex((p) => p.key === currentPhase);

  return (
    <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
      <h3 className="mb-4 text-sm font-semibold text-slate-200">
        10단계 파이프라인
      </h3>

      {/* 데스크탑: 가로 스테퍼 */}
      <div className="hidden items-center md:flex">
        {PHASES.map((phase, i) => {
          const isDone = i < currentIndex;
          const isCurrent = i === currentIndex;
          const isUpcoming = i > currentIndex;

          return (
            <div key={phase.key} className="flex flex-1 items-center">
              <div className="flex flex-col items-center gap-1.5">
                {/* 원형 인디케이터 */}
                <div
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                    isDone
                      ? "bg-emerald-500/20 text-emerald-400"
                      : isCurrent
                        ? "bg-violet-500/20 text-violet-300 ring-2 ring-violet-500/40"
                        : "bg-white/5 text-slate-600"
                  }`}
                >
                  {isDone ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    i + 1
                  )}
                </div>
                {/* 라벨 */}
                <span
                  className={`text-[10px] font-medium ${
                    isDone
                      ? "text-emerald-400/80"
                      : isCurrent
                        ? "text-violet-300"
                        : "text-slate-600"
                  }`}
                >
                  {phase.label}
                </span>
              </div>
              {/* 커넥터 */}
              {i < PHASES.length - 1 && (
                <div
                  className={`mx-1 h-px flex-1 ${
                    isDone
                      ? "bg-emerald-500/30"
                      : isUpcoming
                        ? "bg-white/5"
                        : "bg-violet-500/30"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* 모바일: 프로그레스 바 + 현재 단계 */}
      <div className="md:hidden">
        <div className="mb-2 flex items-center justify-between text-xs">
          <span className="font-medium text-violet-300">
            {PHASES[currentIndex]?.label ?? currentPhase}
          </span>
          <span className="text-slate-500">
            {currentIndex + 1} / {PHASES.length}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-white/5">
          <div
            className="h-full rounded-full bg-violet-500/60 transition-all"
            style={{
              width: `${((currentIndex + 1) / PHASES.length) * 100}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
