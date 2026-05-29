"use client";

import { CheckCircle2, UserCircle2, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";

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
  const t = useTranslations("wizard.pmProfileCard");
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
          ? "border-zinc-900 bg-zinc-50 ring-2 ring-zinc-900/10"
          : "border-zinc-200 bg-zinc-50 hover:border-zinc-300 hover:bg-zinc-100",
      )}
    >
      {/* 우상단: 일치율 배지 (추천 모드) 또는 선택 아이콘 */}
      <div className="absolute right-3 top-3">
        {isSelected ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
        ) : matchScore !== undefined ? (
          <div className="flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5">
            <Sparkles className="h-2.5 w-2.5 text-emerald-600" />
            <span className="text-[10px] font-medium text-emerald-600">
              {t("match", { score: Math.round(matchScore) })}
            </span>
          </div>
        ) : null}
      </div>

      {/* 헤더: 아바타 + 이름 + 전문분야 */}
      <div className="mb-3 flex items-center gap-3 pr-16">
        <div
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-full",
            isSelected ? "bg-emerald-100" : "bg-zinc-50",
          )}
        >
          <UserCircle2
            className={cn(
              "h-6 w-6",
              isSelected ? "text-emerald-600" : "text-zinc-500",
            )}
          />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-zinc-950">
            {profile.name}
          </p>
          <span className="inline-flex items-center rounded-md bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-600">
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
        <p className="mb-3 text-xs leading-relaxed text-zinc-500">
          {profile.description}
        </p>
      )}

      {/* 추천 근거 (인용구 스타일) */}
      {reasoning && (
        <p className="mb-3 rounded-lg bg-zinc-50 px-3 py-2 text-xs italic leading-relaxed text-zinc-500">
          &ldquo;{reasoning}&rdquo;
        </p>
      )}

      {/* 지표 4개 */}
      {metrics && (
        <div className="mb-3 grid grid-cols-4 divide-x divide-zinc-200 rounded-lg bg-zinc-50 px-2 py-2">
          <div className="px-1.5 text-center">
            <p className="text-sm font-semibold text-zinc-950">{totalProjects}</p>
            <p className="text-[10px] text-zinc-500">{t("completedCount")}</p>
          </div>
          <div className="px-1.5 text-center">
            <p className="text-sm font-semibold text-zinc-950">
              {metrics.usage_count}
            </p>
            <p className="text-[10px] text-zinc-500">{t("usageCount")}</p>
          </div>
          <div className="px-1.5 text-center">
            <p className="text-sm font-semibold text-zinc-950">
              {successRate.toFixed(0)}%
            </p>
            <p className="text-[10px] text-zinc-500">{t("successRate")}</p>
          </div>
          <div className="px-1.5 text-center">
            <p className="text-sm font-semibold text-zinc-950">
              {t("daysValue", { days: metrics.avg_completion_days.toFixed(0) })}
            </p>
            <p className="text-[10px] text-zinc-500">{t("avgCompletionDays")}</p>
          </div>
        </div>
      )}

      {/* 전문 분야 태그 */}
      {profile.specialties.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {profile.specialties.slice(0, 4).map((specialty) => (
            <span
              key={specialty}
              className="rounded-md bg-zinc-50 px-2 py-0.5 text-[11px] text-zinc-500"
            >
              {specialty}
            </span>
          ))}
          {profile.specialties.length > 4 && (
            <span className="rounded-md bg-zinc-50 px-2 py-0.5 text-[11px] text-zinc-500">
              +{profile.specialties.length - 4}
            </span>
          )}
        </div>
      )}
    </button>
  );
}
