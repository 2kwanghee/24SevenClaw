"use client";

import { CheckCircle2, UserCircle2, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PMProfileResponse, PMMetricResponse } from "@/lib/api-client";
import { PMRatingStars } from "./pm-rating-stars";

// PMMetricResponse 후방 호환 — pm_id 필드를 사용한다
interface PMProfileCardProps {
  profile: PMProfileResponse;
  metrics?: PMMetricResponse | null;
  matchScore?: number;
  reasoning?: string | null;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

export function PMProfileCard({
  profile,
  metrics,
  matchScore,
  reasoning,
  isSelected,
  onSelect,
}: PMProfileCardProps) {
  const avgRating = metrics?.avg_rating ?? 0;
  const totalProjects = metrics?.completed_projects ?? 0;
  const successRate = metrics?.success_rate ?? 0;

  return (
    <button
      type="button"
      onClick={() => onSelect(profile.id)}
      aria-pressed={isSelected}
      className={cn(
        "group relative w-full rounded-xl border p-4 text-left transition-all duration-200",
        isSelected
          ? "border-emerald-500/50 bg-emerald-500/10 ring-2 ring-emerald-500/20"
          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]",
      )}
    >
      {/* 우상단: 일치율 배지 (추천 모드) 또는 선택 아이콘 */}
      <div className="absolute right-3 top-3">
        {isSelected ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        ) : matchScore !== undefined ? (
          <div className="flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5">
            <Sparkles className="h-2.5 w-2.5 text-emerald-400" />
            <span className="text-[10px] font-medium text-emerald-300">
              {Math.round(matchScore * 100)}% 일치
            </span>
          </div>
        ) : null}
      </div>

      {/* 헤더: 아바타 + 이름 + 전문분야 */}
      <div className="mb-3 flex items-center gap-3 pr-16">
        <div
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-full",
            isSelected ? "bg-emerald-500/20" : "bg-white/5",
          )}
        >
          <UserCircle2
            className={cn(
              "h-6 w-6",
              isSelected ? "text-emerald-300" : "text-slate-400",
            )}
          />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">
            {profile.name}
          </p>
          <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-medium text-emerald-400">
            {profile.specialties?.[0] ?? profile.domain ?? profile.title ?? ""}
          </span>
        </div>
      </div>

      {/* 별점 */}
      {metrics && (
        <div className="mb-3">
          <PMRatingStars rating={avgRating} showValue />
        </div>
      )}

      {/* 설명 */}
      {profile.description && (
        <p className="mb-3 text-xs leading-relaxed text-slate-400">
          {profile.description}
        </p>
      )}

      {/* 추천 근거 (인용구 스타일) */}
      {reasoning && (
        <p className="mb-3 rounded-lg bg-white/[0.03] px-3 py-2 text-xs italic leading-relaxed text-slate-500">
          &ldquo;{reasoning}&rdquo;
        </p>
      )}

      {/* 지표 3개 */}
      {metrics && (
        <div className="mb-3 grid grid-cols-3 divide-x divide-white/5 rounded-lg bg-white/[0.03] px-2 py-2">
          <div className="px-2 text-center">
            <p className="text-sm font-semibold text-white">{totalProjects}</p>
            <p className="text-[10px] text-slate-500">완료건수</p>
          </div>
          <div className="px-2 text-center">
            <p className="text-sm font-semibold text-white">
              {(successRate * 100).toFixed(0)}%
            </p>
            <p className="text-[10px] text-slate-500">성공률</p>
          </div>
          <div className="px-2 text-center">
            <p className="text-sm font-semibold text-white">
              {avgRating.toFixed(1)}
            </p>
            <p className="text-[10px] text-slate-500">평균 별점</p>
          </div>
        </div>
      )}

      {/* 전문 분야 태그 */}
      {profile.specialties.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {profile.specialties.slice(0, 4).map((specialty) => (
            <span
              key={specialty}
              className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-slate-500"
            >
              {specialty}
            </span>
          ))}
          {profile.specialties.length > 4 && (
            <span className="rounded-md bg-white/5 px-2 py-0.5 text-[11px] text-slate-600">
              +{profile.specialties.length - 4}
            </span>
          )}
        </div>
      )}
    </button>
  );
}
