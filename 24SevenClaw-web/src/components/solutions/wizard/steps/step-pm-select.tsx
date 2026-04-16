"use client";

import { Loader2, UserCircle2, Info, CheckCircle2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import {
  pmProfiles,
  type PMProfileResponse,
  type PMMetricResponse,
} from "@/lib/api-client";
import { PMProfileCard } from "../pm-profile-card";
import { PMCompositionView } from "../pm-composition-view";

/** 추천 목록의 각 항목 (프로필 + 지표 + 추천 정보) */
interface PMListItem {
  profile: PMProfileResponse;
  metrics: PMMetricResponse | null;
  matchScore?: number;
  reasoning?: string | null;
}

const LOADING_STEPS = [
  "프로토타입 요구사항 분석 중...",
  "PM 프로필 매칭 중...",
  "최적 PM 선정 완료 중...",
] as const;

export function StepPMSelect() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const selectedPrototypeId = useSolutionWizardStore(
    (s) => s.data.prototypes.selectedPrototypeId,
  );
  const selectedPmProfileId = useSolutionWizardStore(
    (s) => s.data.pm.selectedPmProfileId,
  );
  const setPM = useSolutionWizardStore((s) => s.setPM);

  const [items, setItems] = useState<PMListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);

  const selectedItem = items.find((i) => i.profile.id === selectedPmProfileId);

  /* 로딩 단계 애니메이션 */
  useEffect(() => {
    if (!isLoading) return;
    const timer = setInterval(() => {
      setLoadingStep((prev) =>
        prev < LOADING_STEPS.length - 1 ? prev + 1 : prev,
      );
    }, 900);
    return () => clearInterval(timer);
  }, [isLoading]);

  /* PM 추천 및 지표 조회 */
  useEffect(() => {
    if (!token) return;

    const fetchItems = async () => {
      setIsLoading(true);
      setLoadingStep(0);

      try {
        let profiles: PMProfileResponse[] = [];
        const recommendMap: Record<
          string,
          { matchScore: number; reasoning: string | null }
        > = {};

        if (selectedPrototypeId) {
          const result = await pmProfiles.recommend(token, {
            prototype_id: selectedPrototypeId,
          });
          profiles = result.items.map((r) => r.pm_profile);
          result.items.forEach((r) => {
            recommendMap[r.pm_profile.id] = {
              matchScore: r.match_score,
              reasoning: r.reasoning,
            };
          });
        } else {
          const result = await pmProfiles.list(token, {
            is_active: true,
            limit: 10,
          });
          profiles = result.items;
        }

        /* 각 프로필의 지표를 병렬 조회 */
        const metricsResults = await Promise.allSettled(
          profiles.map((p) => pmProfiles.getMetrics(token, p.id)),
        );

        const enriched: PMListItem[] = profiles.map((profile, i) => ({
          profile,
          metrics:
            metricsResults[i].status === "fulfilled"
              ? (metricsResults[i] as PromiseFulfilledResult<PMMetricResponse>)
                  .value
              : null,
          matchScore: recommendMap[profile.id]?.matchScore,
          reasoning: recommendMap[profile.id]?.reasoning,
        }));

        setItems(enriched);
      } catch {
        setItems([]);
      } finally {
        setIsLoading(false);
      }
    };

    void fetchItems();
  }, [token, selectedPrototypeId]);

  /* ── 로딩 상태 ─────────────────────────────────── */
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="relative mb-6">
          <div className="h-16 w-16 animate-pulse rounded-full border border-emerald-500/20 bg-emerald-500/5" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="h-7 w-7 animate-spin text-emerald-400" />
          </div>
        </div>
        <p className="mb-1 text-sm font-semibold text-white">
          PM 추천 분석 중...
        </p>
        <p className="mb-8 text-xs text-slate-500">
          프로토타입에 최적화된 PM 프로필을 탐색하고 있습니다
        </p>
        <div className="w-full max-w-xs space-y-3">
          {LOADING_STEPS.map((label, idx) => (
            <div
              key={label}
              className={`flex items-center gap-2.5 text-sm transition-all duration-300 ${
                idx < loadingStep
                  ? "text-emerald-400"
                  : idx === loadingStep
                    ? "text-white"
                    : "text-slate-600"
              }`}
            >
              {idx < loadingStep ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              ) : idx === loadingStep ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-emerald-400" />
              ) : (
                <div className="h-4 w-4 shrink-0 rounded-full border border-slate-700" />
              )}
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  /* ── 빈 상태 ─────────────────────────────────── */
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <UserCircle2 className="h-10 w-10 text-slate-600" />
        <p className="mt-4 text-sm text-slate-400">
          추천 가능한 PM 프로필이 없습니다
        </p>
      </div>
    );
  }

  /* ── 정상 상태 ─────────────────────────────────── */
  return (
    <div className="space-y-5">
      {/* 추천 안내 배너 */}
      {selectedPrototypeId && (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          <p className="text-xs text-slate-400">
            선택한 프로토타입 기반으로 AI가 최적의 PM을 추천했습니다. 일치율이
            높을수록 프로젝트 성공 가능성이 높습니다.
          </p>
        </div>
      )}

      {/* PM 카드 그리드 */}
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((item) => (
          <PMProfileCard
            key={item.profile.id}
            profile={item.profile}
            metrics={item.metrics}
            matchScore={item.matchScore}
            reasoning={item.reasoning}
            isSelected={selectedPmProfileId === item.profile.id}
            onSelect={(id) => setPM({ selectedPmProfileId: id })}
          />
        ))}
      </div>

      {/* PM 구성 시각화 (선택 후 표시) */}
      {selectedItem && (
        <div className="animate-fade-in-up space-y-3">
          <div className="flex items-center gap-2 text-xs text-emerald-400">
            <Sparkles className="h-3.5 w-3.5" />
            <span>선택한 PM의 구성 요소</span>
          </div>
          <PMCompositionView profile={selectedItem.profile} />
        </div>
      )}
    </div>
  );
}
