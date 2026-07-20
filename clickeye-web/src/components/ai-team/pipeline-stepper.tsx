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
    <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
      <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">
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
                      ? "bg-emerald-50 text-emerald-700"
                      : isCurrent
                        ? "bg-[var(--accent)] text-[var(--accent-fg)] ring-2 ring-[var(--accent-soft)]"
                        : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
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
                      ? "text-emerald-700"
                      : isCurrent
                        ? "text-[var(--text-primary)]"
                        : "text-[var(--text-muted)]"
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
                      ? "bg-emerald-200"
                      : isUpcoming
                        ? "bg-[var(--border-subtle)]"
                        : "bg-[var(--border-medium)]"
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
          <span className="font-medium text-[var(--text-primary)]">
            {PHASES[currentIndex]?.label ?? currentPhase}
          </span>
          <span className="text-[var(--text-muted)]">
            {currentIndex + 1} / {PHASES.length}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-[var(--bg-hover)]">
          <div
            className="h-full rounded-full bg-[var(--accent)] transition-all"
            style={{
              width: `${((currentIndex + 1) / PHASES.length) * 100}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
