"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Info, Sparkles, UserCircle2 } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import {
  pmProfiles,
  prototypeSessions,
  type PMProfileWithMetrics,
  type PMMetricResponse,
} from "@/lib/api-client";
import { PMProfileCard } from "../pm-profile-card";
import { PMCompositionView } from "../pm-composition-view";

/* -- 타입 -------------------------------------------------------------- */

interface PMListItem {
  profile: PMProfileWithMetrics;
  metrics: PMMetricResponse;
  matchScore?: number;
  reasoning?: string;
}

/* -- 헬퍼: PMProfileWithMetrics → PMMetricResponse 변환 --------------- */

function toMetricResponse(p: PMProfileWithMetrics): PMMetricResponse {
  return {
    id: p.id,
    pm_id: p.id,
    usage_count: p.usage_count,
    completed_projects: p.completed_projects,
    avg_rating: p.avg_rating,
    total_ratings: p.total_ratings,
    success_rate: p.success_rate,
    avg_completion_days: p.avg_completion_days,
  };
}

/* -- 메인 컴포넌트 ----------------------------------------------------- */

/**
 * Step 5: PM 선택
 *
 * - Step 4(PM 추천)에서 저장된 추천 목록을 읽어 PM 카드 표시
 * - 추천 목록이 없으면 POST recommend-pms를 재호출(폴백)
 * - 카드 클릭 → 선택 하이라이트 + PATCH /prototype-sessions/{id} (selected_pm_id)
 */
export function StepPMSelection() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);
  const recommendedItems = useSolutionWizardStore(
    (s) => s.data.pm.recommendedItems,
  );
  const selectedPmProfileId = useSolutionWizardStore(
    (s) => s.data.pm.selectedPmProfileId,
  );
  const setPM = useSolutionWizardStore((s) => s.setPM);
  const setRecommendedPMItems = useSolutionWizardStore(
    (s) => s.setRecommendedPMItems,
  );

  const [items, setItems] = useState<PMListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const selectedItem = items.find(
    (i) => i.profile.id === selectedPmProfileId,
  );

  /* -- PM 목록 로드 -- */
  useEffect(() => {
    if (!token) return;

    const fetchItems = async () => {
      setIsLoading(true);

      try {
        let pmIds: { pmId: string; matchScore?: number; reasoning?: string }[];

        if (recommendedItems.length > 0) {
          // 캐시된 추천 결과 사용
          pmIds = recommendedItems.map((r) => ({
            pmId: r.pmId,
            matchScore: r.matchScore,
            reasoning: r.reasoning,
          }));
        } else {
          // 폴백: recommend API 재호출
          if (sessionId) {
            const result = await prototypeSessions.recommendPMs(
              token,
              sessionId,
            );
            const mapped = result.items.map((item) => ({
              pmId: item.pm_id,
              name: item.name,
              slug: item.slug,
              avatarUrl: item.avatar_url,
              title: item.title,
              domain: item.domain,
              matchScore: item.match_score,
              reasoning: item.reasoning,
            }));
            setRecommendedPMItems(mapped);
            pmIds = mapped.map((r) => ({
              pmId: r.pmId,
              matchScore: r.matchScore,
              reasoning: r.reasoning,
            }));
          } else {
            // 세션 없음: 일반 목록 조회
            const listResult = await pmProfiles.list(token, {
              is_active: true,
              limit: 6,
            });
            pmIds = listResult.items.map((p) => ({ pmId: p.id }));
          }
        }

        // 각 PM의 전체 프로필(지표 포함) 병렬 조회
        const profileResults = await Promise.allSettled(
          pmIds.map(({ pmId }) => pmProfiles.get(token, pmId)),
        );

        const enriched: PMListItem[] = [];
        profileResults.forEach((result, i) => {
          if (result.status === "fulfilled") {
            const profile = result.value;
            enriched.push({
              profile,
              metrics: toMetricResponse(profile),
              matchScore: pmIds[i]?.matchScore,
              reasoning: pmIds[i]?.reasoning,
            });
          }
        });

        setItems(enriched);
      } catch {
        setItems([]);
      } finally {
        setIsLoading(false);
      }
    };

    void fetchItems();
  }, [token, sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  /* -- 선택 핸들러 -- */
  const handleSelect = (pmProfileId: string) => {
    setPM({ selectedPmProfileId: pmProfileId });

    // 낙관적 업데이트: fire-and-forget
    if (sessionId && token) {
      void prototypeSessions
        .update(token, sessionId, { selected_pm_id: pmProfileId })
        .catch(() => {
          // 실패해도 로컬 상태 유지
        });
    }
  };

  /* -- 로딩 상태: 스켈레톤 카드 그리드 ------------------------------- */
  if (isLoading) {
    return (
      <div className="space-y-5">
        {recommendedItems.length > 0 && (
          <div className="h-10 animate-pulse rounded-xl bg-white/[0.03]" aria-hidden="true" />
        )}
        <div className="grid gap-3 sm:grid-cols-2" aria-busy="true" aria-label="PM 프로필 불러오는 중">
          {Array.from({ length: recommendedItems.length > 0 ? recommendedItems.length : 3 }, (_, i) => (
            <div
              key={i}
              className="animate-pulse rounded-xl border border-white/5 bg-white/[0.02] p-4"
              style={{ animationDelay: `${i * 100}ms` }}
              aria-hidden="true"
            >
              <div className="mb-3 flex items-start gap-3">
                <div className="h-12 w-12 shrink-0 rounded-full bg-white/[0.07]" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-32 rounded-md bg-white/[0.07]" />
                  <div className="h-3 w-20 rounded-full bg-white/[0.05]" />
                </div>
              </div>
              <div className="mb-3 space-y-1.5">
                <div className="h-3 w-full rounded-md bg-white/[0.05]" />
                <div className="h-3 w-4/5 rounded-md bg-white/[0.05]" />
              </div>
              <div className="grid grid-cols-4 gap-2 rounded-lg bg-white/[0.03] p-2">
                {Array.from({ length: 4 }, (_, j) => (
                  <div key={j} className="space-y-1 text-center">
                    <div className="mx-auto h-4 w-8 rounded-md bg-white/[0.07]" />
                    <div className="mx-auto h-2.5 w-10 rounded-md bg-white/[0.05]" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  /* -- 빈 상태 ------------------------------------------------------- */
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

  /* -- 정상 상태 ------------------------------------------------------- */
  return (
    <div className="space-y-5">
      {/* 추천 안내 배너 */}
      {recommendedItems.length > 0 && (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          <p className="text-xs text-slate-400">
            선택한 프로토타입 기반으로 AI가 최적의 PM을 추천했습니다. 일치율이
            높을수록 프로젝트 성공 가능성이 높습니다.
          </p>
        </div>
      )}

      {/* PM 카드 그리드 */}
      <div className="grid gap-3 sm:grid-cols-2" role="list" aria-label="PM 프로필 목록">
        {items.map((item) => (
          <PMProfileCard
            key={item.profile.id}
            profile={item.profile}
            metrics={item.metrics}
            matchScore={item.matchScore}
            reasoning={item.reasoning}
            isSelected={selectedPmProfileId === item.profile.id}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {/* PM 구성 시각화 (선택 후 표시) */}
      {selectedItem && (
        <div className="animate-in fade-in slide-in-from-bottom-2 space-y-3">
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
