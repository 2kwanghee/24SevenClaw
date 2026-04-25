"use client";

import { CheckCircle2, ChevronRight, Star, ThumbsUp, ThumbsDown } from "lucide-react";

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
  { badge: string; ring: string; bg: string; border: string; check: string }
> = {
  saas: {
    badge: "text-sky-300 border-sky-500/30 bg-sky-500/10",
    ring: "ring-sky-500/20",
    bg: "bg-sky-500/5",
    border: "border-sky-500/40",
    check: "text-sky-400",
  },
  "rest-api": {
    badge: "text-violet-300 border-violet-500/30 bg-violet-500/10",
    ring: "ring-violet-500/20",
    bg: "bg-violet-500/5",
    border: "border-violet-500/40",
    check: "text-violet-400",
  },
  fullstack: {
    badge: "text-emerald-600 border-emerald-200 bg-emerald-50",
    ring: "ring-emerald-500/20",
    bg: "bg-emerald-500/5",
    border: "border-zinc-900",
    check: "text-emerald-600",
  },
  "internal-tool": {
    badge: "text-amber-300 border-amber-500/30 bg-amber-500/10",
    ring: "ring-amber-500/20",
    bg: "bg-amber-500/5",
    border: "border-amber-500/40",
    check: "text-amber-400",
  },
  mvp: {
    badge: "text-rose-300 border-rose-500/30 bg-rose-500/10",
    ring: "ring-rose-500/20",
    bg: "bg-rose-500/5",
    border: "border-rose-500/40",
    check: "text-rose-400",
  },
  custom: {
    badge: "text-zinc-700 border-zinc-300 bg-zinc-100",
    ring: "ring-zinc-300",
    bg: "bg-zinc-50",
    border: "border-zinc-200",
    check: "text-zinc-500",
  },
};

function getTypeStyle(solutionType: string) {
  return SOLUTION_TYPE_COLORS[solutionType] ?? SOLUTION_TYPE_COLORS.custom;
}

interface PrototypeCardProps {
  prototype: PrototypeOption;
  isSelected: boolean;
  /** 선택 시 프리뷰 확대 여부 */
  isExpanded?: boolean;
  onSelect: (id: string) => void;
}

export function PrototypeCard({
  prototype,
  isSelected,
  isExpanded = false,
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
          ? cn("ring-2", style.ring, style.bg, style.border)
          : "border-zinc-200 bg-zinc-50 hover:border-zinc-300 hover:bg-zinc-100",
      )}
    >
      {/* 헤더: 이름 + 유형 배지 + 선택 아이콘 */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-zinc-950">
              {prototype.name}
            </span>
            {/* 추천 배지 */}
            {prototype.isRecommended && (
              <span className="inline-flex shrink-0 items-center gap-1 rounded-md border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 text-xs font-medium text-yellow-300">
                <Star className="h-2.5 w-2.5" aria-hidden="true" />
                추천
              </span>
            )}
            {/* 디자인 패턴 배지 */}
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

          {/* 아키텍처 패턴 */}
          {prototype.architecturePattern && (
            <p className="text-[11px] font-medium text-zinc-500">
              {prototype.architecturePattern}
            </p>
          )}

          {/* 근거 (1줄) */}
          {prototype.rationale && (
            <p className="line-clamp-1 text-xs italic text-zinc-500">
              {prototype.rationale}
            </p>
          )}

          {/* AI 추론 설명 (description) */}
          {prototype.reasoning && (
            <p className="text-xs leading-relaxed text-zinc-500">
              {prototype.reasoning}
            </p>
          )}

          {/* 기술 스택 뱃지 */}
          {prototype.techStack && prototype.techStack.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-0.5">
              {prototype.techStack.slice(0, 5).map((tech) => (
                <span
                  key={tech}
                  className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[10px] text-zinc-500"
                >
                  {tech}
                </span>
              ))}
              {prototype.techStack.length > 5 && (
                <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[10px] text-zinc-500">
                  +{prototype.techStack.length - 5}
                </span>
              )}
            </div>
          )}

          {/* 장단점 */}
          {((prototype.pros && prototype.pros.length > 0) || (prototype.cons && prototype.cons.length > 0)) && (
            <div className="mt-2 space-y-1.5 rounded-lg border border-zinc-100 bg-zinc-50 p-2.5">
              {prototype.pros && prototype.pros.length > 0 && (
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1 mb-1">
                    <ThumbsUp className="h-2.5 w-2.5 text-emerald-500" aria-hidden="true" />
                    <span className="text-[10px] font-medium text-emerald-500">장점</span>
                  </div>
                  {prototype.pros.map((pro, i) => (
                    <p key={i} className="text-[11px] leading-relaxed text-zinc-500 pl-3.5">
                      {pro}
                    </p>
                  ))}
                </div>
              )}
              {prototype.cons && prototype.cons.length > 0 && (
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1 mb-1">
                    <ThumbsDown className="h-2.5 w-2.5 text-amber-500" aria-hidden="true" />
                    <span className="text-[10px] font-medium text-amber-500">단점</span>
                  </div>
                  {prototype.cons.map((con, i) => (
                    <p key={i} className="text-[11px] leading-relaxed text-zinc-500 pl-3.5">
                      {con}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 선택 상태 아이콘 */}
        <div className="shrink-0 mt-0.5">
          {isSelected ? (
            <CheckCircle2 className={cn("h-5 w-5", style.check)} />
          ) : (
            <ChevronRight className="h-5 w-5 text-zinc-500 transition-colors group-hover:text-zinc-500" />
          )}
        </div>
      </div>

      {/* 아키텍처 / UI 구조 프리뷰 */}
      <div className={cn("mt-3 transition-all duration-300", isExpanded && "mt-4")}>
        <PrototypePreview
          config={prototype.config}
          solutionType={prototype.solutionType}
          isExpanded={isExpanded}
        />
      </div>
    </button>
  );
}
