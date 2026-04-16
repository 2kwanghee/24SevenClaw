"use client";

import { CheckCircle2, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PrototypeOption } from "@/types/solution-wizard";
import { PrototypePreview } from "./prototype-preview";

const SOLUTION_TYPE_LABELS: Record<string, string> = {
  saas: "SaaS",
  "rest-api": "REST API",
  fullstack: "풀스택 웹",
  "internal-tool": "내부 도구",
  mvp: "MVP",
  custom: "커스텀",
};

const SOLUTION_TYPE_COLORS: Record<
  string,
  { badge: string; ring: string; bg: string; border: string }
> = {
  saas: {
    badge: "text-sky-300 border-sky-500/30 bg-sky-500/10",
    ring: "ring-sky-500/20",
    bg: "bg-sky-500/5",
    border: "border-sky-500/40",
  },
  "rest-api": {
    badge: "text-violet-300 border-violet-500/30 bg-violet-500/10",
    ring: "ring-violet-500/20",
    bg: "bg-violet-500/5",
    border: "border-violet-500/40",
  },
  fullstack: {
    badge: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10",
    ring: "ring-emerald-500/20",
    bg: "bg-emerald-500/5",
    border: "border-emerald-500/40",
  },
  "internal-tool": {
    badge: "text-amber-300 border-amber-500/30 bg-amber-500/10",
    ring: "ring-amber-500/20",
    bg: "bg-amber-500/5",
    border: "border-amber-500/40",
  },
  mvp: {
    badge: "text-rose-300 border-rose-500/30 bg-rose-500/10",
    ring: "ring-rose-500/20",
    bg: "bg-rose-500/5",
    border: "border-rose-500/40",
  },
  custom: {
    badge: "text-slate-300 border-slate-500/30 bg-slate-500/10",
    ring: "ring-slate-500/20",
    bg: "bg-slate-500/5",
    border: "border-slate-500/40",
  },
};

function getTypeStyle(solutionType: string) {
  return SOLUTION_TYPE_COLORS[solutionType] ?? SOLUTION_TYPE_COLORS.custom;
}

interface PrototypeCardProps {
  prototype: PrototypeOption;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export function PrototypeCard({
  prototype,
  isSelected,
  onSelect,
}: PrototypeCardProps) {
  const style = getTypeStyle(prototype.solutionType);

  return (
    <button
      type="button"
      onClick={() => onSelect(prototype.id)}
      aria-pressed={isSelected}
      className={cn(
        "group w-full rounded-xl border p-4 text-left transition-all duration-200",
        isSelected
          ? cn(
              "ring-2",
              style.ring,
              style.bg,
              style.border,
            )
          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]",
      )}
    >
      {/* 헤더: 이름 + 유형 배지 + 선택 아이콘 */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-white">
              {prototype.name}
            </span>
            <span
              className={cn(
                "inline-flex shrink-0 items-center rounded-md border px-2 py-0.5 text-xs font-medium",
                style.badge,
              )}
            >
              {SOLUTION_TYPE_LABELS[prototype.solutionType] ??
                prototype.solutionType}
            </span>
          </div>

          {/* AI 추론 설명 */}
          {prototype.reasoning && (
            <p className="text-xs leading-relaxed text-slate-400">
              {prototype.reasoning}
            </p>
          )}
        </div>

        {/* 선택 상태 아이콘 */}
        <div className="shrink-0 mt-0.5">
          {isSelected ? (
            <CheckCircle2
              className={cn("h-5 w-5", `text-${prototype.solutionType === "saas" ? "sky" : prototype.solutionType === "rest-api" ? "violet" : prototype.solutionType === "mvp" ? "rose" : "emerald"}-400`)}
            />
          ) : (
            <ChevronRight className="h-5 w-5 text-slate-600 transition-colors group-hover:text-slate-400" />
          )}
        </div>
      </div>

      {/* 아키텍처 프리뷰 */}
      <div className="mt-3">
        <PrototypePreview
          config={prototype.config}
          solutionType={prototype.solutionType}
        />
      </div>
    </button>
  );
}
