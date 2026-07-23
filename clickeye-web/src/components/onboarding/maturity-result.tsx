"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Trophy, ArrowRight, Settings2, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";
import { MaturityBadge } from "@/components/presets/maturity-badge";
import type { MaturityAssessmentResponse } from "@/lib/api-client";

function useAnimatedScore(targetScore: number, duration = 1500) {
  const [score, setScore] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const startTime = performance.now();
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setScore(Math.round(eased * targetScore));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    requestAnimationFrame(animate);
  }, [targetScore, duration]);

  return score;
}

interface MaturityResultProps {
  result: MaturityAssessmentResponse;
}

export function MaturityResult({ result }: MaturityResultProps) {
  const router = useRouter();
  const t = useTranslations("onboarding.maturityResult");
  const animatedScore = useAnimatedScore(result.score);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowDetails(true), 1200);
    return () => clearTimeout(timer);
  }, []);

  const scoreColor =
    result.level === "starter"
      ? "text-emerald-600"
      : result.level === "intermediate"
        ? "text-blue-600"
        : "text-amber-600";

  const ringColor =
    result.level === "starter"
      ? "border-emerald-200"
      : result.level === "intermediate"
        ? "border-blue-200"
        : "border-amber-200";

  const glowClass =
    result.level === "starter"
      ? "shadow-emerald-500/10"
      : result.level === "intermediate"
        ? "shadow-blue-500/10"
        : "shadow-amber-500/10";

  return (
    <div className="flex flex-col items-center">
      {/* 점수 원형 */}
      <div
        className={cn(
          "relative flex h-40 w-40 flex-col items-center justify-center rounded-full border-4 shadow-2xl transition-all duration-1000",
          ringColor,
          glowClass,
        )}
      >
        <span className={cn("text-5xl font-bold tabular-nums", scoreColor)}>
          {animatedScore}
        </span>
        <span className="text-xs text-[var(--text-muted)]">/ 100</span>
      </div>

      {/* 배지 */}
      <div className="mt-5 flex items-center gap-2">
        <Trophy className={cn("h-5 w-5", scoreColor)} />
        <MaturityBadge level={result.level} className="px-3 py-1 text-sm" />
      </div>

      {/* 상세 정보 (페이드 인) */}
      <div
        className={cn(
          "mt-8 w-full max-w-md space-y-6 transition-all duration-700",
          showDetails
            ? "translate-y-0 opacity-100"
            : "translate-y-4 opacity-0",
        )}
      >
        {/* 분석 결과 */}
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
            {result.reasoning}
          </p>
        </div>

        {/* CTA 버튼 */}
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => {
              const params = result.recommended_preset_id
                ? `?recommended=${result.recommended_preset_id}`
                : "";
              router.push(`/onboarding/preset${params}`);
            }}
            className="group flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-[var(--accent-fg)] shadow-lg transition-all hover:bg-[var(--accent-hover)]"
          >
            <Sparkles className="h-4 w-4" />
            {t("viewPresets")}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </button>

          <button
            type="button"
            onClick={() => router.push("/delivery")}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--border-subtle)] px-5 py-3 text-sm text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <Settings2 className="h-4 w-4" />
            {t("configureManually")}
          </button>
        </div>
      </div>
    </div>
  );
}
