"use client";

import { Bot, Wrench, GitBranch, ArrowRight, Check } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PresetResponse } from "@/lib/api-client";

import { MaturityBadge } from "./maturity-badge";

interface PresetCardProps {
  preset: PresetResponse;
  selected?: boolean;
  recommended?: boolean;
  onSelect: (preset: PresetResponse) => void;
}

export function PresetCard({
  preset,
  selected = false,
  recommended = false,
  onSelect,
}: PresetCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(preset)}
      aria-pressed={selected}
      aria-label={`${preset.name} 프리셋 ${selected ? "선택됨" : "선택"}`}
      className={cn(
        "relative flex flex-col gap-4 rounded-xl border px-5 py-5 text-left transition-all duration-200",
        "hover:scale-[1.02] active:scale-[0.98]",
        selected
          ? "border-violet-300 bg-violet-50 shadow-lg shadow-violet-500/10 ring-2 ring-violet-200"
          : "border-[var(--border-subtle)] bg-[var(--bg-surface)] hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)]",
      )}
    >
      {/* 선택 표시 */}
      {selected && (
        <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900">
          <Check className="h-3 w-3 text-white" />
        </div>
      )}

      {/* 추천 배지 */}
      {recommended && !selected && (
        <span className="absolute right-3 top-3 rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
          추천
        </span>
      )}

      {/* 헤더: 이름 + 성숙도 배지 */}
      <div className="flex items-center gap-3">
        <h3 className="text-base font-semibold text-[var(--text-primary)]">{preset.name}</h3>
        <MaturityBadge level={preset.maturity_level} />
      </div>

      {/* 설명 */}
      {preset.description && (
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
          {preset.description}
        </p>
      )}

      {/* 구성 요소 요약 */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <Bot className="h-3.5 w-3.5" />
          <span>에이전트 {preset.default_agents.length}개</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <Wrench className="h-3.5 w-3.5" />
          <span>스킬 {preset.default_skills.length}개</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <GitBranch className="h-3.5 w-3.5" />
          <span>파이프라인 {preset.default_pipelines.length}개</span>
        </div>
      </div>

      {/* CTA */}
      <div
        className={cn(
          "flex items-center gap-1.5 text-xs font-medium transition-colors",
          selected ? "text-violet-600" : "text-[var(--text-muted)]",
        )}
      >
        {selected ? "선택됨" : "이 프리셋으로 시작하기"}
        {!selected && <ArrowRight className="h-3 w-3" />}
      </div>
    </button>
  );
}
