"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  UserCircle2,
} from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { prototypeSessions, ApiClientError } from "@/lib/api-client";
import type { PMRecommendedItem } from "@/types/solution-wizard";

/* ── 상수 ────────────────────────────────────────────────────────────── */

const EXPECTED_COUNT = 3;

/* ── 스켈레톤 카드 ───────────────────────────────────────────────────── */

function PMSkeletonCard({ index }: { index: number }) {
  return (
    <div
      className="animate-pulse rounded-xl border border-white/5 bg-white/[0.02] p-4"
      style={{ animationDelay: `${index * 120}ms` }}
      aria-hidden="true"
    >
      <div className="mb-3 flex items-center gap-3 pr-16">
        <div className="h-11 w-11 shrink-0 rounded-full bg-white/[0.07]" />
        <div className="space-y-1.5">
          <div className="h-3.5 w-28 rounded-md bg-white/[0.07]" />
          <div className="h-2.5 w-20 rounded-full bg-white/[0.05]" />
        </div>
      </div>
      <div className="mb-3 flex gap-1">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="h-3 w-3 rounded-sm bg-white/[0.07]" />
        ))}
      </div>
      <div className="mb-3 space-y-1.5">
        <div className="h-3 w-full rounded-md bg-white/[0.05]" />
        <div className="h-3 w-4/5 rounded-md bg-white/[0.05]" />
      </div>
      <div className="mb-3 grid grid-cols-4 divide-x divide-white/5 rounded-lg bg-white/[0.03] px-2 py-2">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="space-y-1 px-1.5 text-center">
            <div className="mx-auto h-4 w-8 rounded-md bg-white/[0.07]" />
            <div className="mx-auto h-2.5 w-10 rounded-md bg-white/[0.05]" />
          </div>
        ))}
      </div>
      <div className="flex gap-1.5">
        <div className="h-5 w-16 rounded-md bg-white/[0.05]" />
        <div className="h-5 w-20 rounded-md bg-white/[0.05]" />
        <div className="h-5 w-14 rounded-md bg-white/[0.05]" />
      </div>
    </div>
  );
}

/* ── 완료 카드 ───────────────────────────────────────────────────────── */

interface PMReadyCardProps {
  item: PMRecommendedItem;
  index: number;
}

function PMReadyCard({ item, index }: PMReadyCardProps) {
  return (
    <div
      className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 animate-in fade-in slide-in-from-bottom-2"
      style={{ animationDelay: `${index * 100}ms`, animationDuration: "400ms" }}
      role="status"
      aria-label={`PM "${item.name}" 분석 완료`}
    >
      <div className="mb-2 flex items-center gap-3 pr-12">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-500/15">
          <UserCircle2 className="h-6 w-6 text-emerald-300" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{item.name}</p>
          {item.title && (
            <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-medium text-emerald-400">
              {item.title}
            </span>
          )}
        </div>
        <div className="absolute right-7 top-4">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
        </div>
      </div>
      <p className="line-clamp-1 text-xs text-slate-500 italic">&ldquo;{item.reasoning}&rdquo;</p>
    </div>
  );
}

/* ── 메인 컴포넌트 ───────────────────────────────────────────────────── */

/**
 * Step 4: PM 추천
 *
 * - POST /prototype-sessions/{id}/recommend-pms 호출
 * - 로딩 중 스켈레톤 카드 표시
 * - 완료 시 스토어에 저장 → 자동으로 Step 5(PM 선택)로 전환
 */
export function StepPMRecommendation() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);
  const existingItems = useSolutionWizardStore(
    (s) => s.data.pm.recommendedItems,
  );
  const setRecommendedPMItems = useSolutionWizardStore(
    (s) => s.setRecommendedPMItems,
  );
  const nextStep = useSolutionWizardStore((s) => s.nextStep);

  const [items, setItems] = useState<PMRecommendedItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isFailed, setIsFailed] = useState(false);

  const cancelledRef = useRef(false);
  const hasStartedRef = useRef(false);

  /* ── 추천 실행 ── */
  const startRecommendation = useCallback(async () => {
    if (!sessionId || !token) return;
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    cancelledRef.current = false;
    setIsLoading(true);
    setIsFailed(false);
    setItems([]);

    try {
      const result = await prototypeSessions.recommendPMs(token, sessionId);

      if (cancelledRef.current) return;

      const recommended: PMRecommendedItem[] = result.items.map((item) => ({
        pmId: item.pm_id,
        name: item.name,
        slug: item.slug,
        avatarUrl: item.avatar_url,
        title: item.title,
        domain: item.domain,
        matchScore: item.match_score,
        reasoning: item.reasoning,
      }));

      setItems(recommended);
      setRecommendedPMItems(recommended);
      setIsLoading(false);

      // 짧은 딜레이 후 자동 이동
      await new Promise<void>((res) => setTimeout(res, 700));
      if (!cancelledRef.current) {
        nextStep();
      }
    } catch (err) {
      if (cancelledRef.current) return;
      if (err instanceof ApiClientError && err.status === 409) {
        // 이미 처리된 경우 — 스킵하고 다음 단계로
        nextStep();
        return;
      }
      setIsLoading(false);
      setIsFailed(true);
    }
  }, [sessionId, token, setRecommendedPMItems, nextStep]);

  /* ── 이미 추천 결과가 있으면 즉시 이동 ── */
  useEffect(() => {
    if (existingItems.length > 0) {
      nextStep();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── 마운트 시 추천 시작 ── */
  useEffect(() => {
    if (existingItems.length > 0) return;

    cancelledRef.current = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void startRecommendation();
    return () => {
      cancelledRef.current = true;
    };
  }, [startRecommendation, existingItems.length]);

  /* ── 재시도 ── */
  const handleRetry = () => {
    hasStartedRef.current = false;
    void startRecommendation();
  };

  /* ── 실패 상태 ─────────────────────────────────────────────────────── */
  if (isFailed) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-rose-500/20 bg-rose-500/10">
          <AlertCircle className="h-7 w-7 text-rose-400" aria-hidden="true" />
        </div>
        <h3 className="mb-1 text-sm font-semibold text-rose-300">
          PM 추천 분석에 실패했습니다
        </h3>
        <p className="mb-6 text-xs text-slate-500">
          일시적인 오류가 발생했습니다. 다시 시도해 주세요.
        </p>
        <button
          type="button"
          onClick={handleRetry}
          className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-medium text-slate-300 transition-all hover:border-white/20 hover:bg-white/[0.07] hover:text-white"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          다시 시도
        </button>
      </div>
    );
  }

  const isDone = !isLoading && items.length > 0;
  const displayCount = Math.max(items.length || EXPECTED_COUNT, EXPECTED_COUNT);

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-2.5">
        {isDone ? (
          <CheckCircle2 className="h-5 w-5 text-emerald-400" aria-hidden="true" />
        ) : (
          <Loader2 className="h-5 w-5 animate-spin text-emerald-400" aria-hidden="true" />
        )}
        <span className="text-sm font-medium text-slate-300">
          {isDone
            ? "PM 추천 분석 완료!"
            : "프로토타입에 최적화된 PM을 분석하고 있습니다"}
        </span>
      </div>

      {/* 진행률 바 */}
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-valuenow={isDone ? displayCount : 0}
        aria-valuemin={0}
        aria-valuemax={displayCount}
        aria-label="PM 추천 분석 진행률"
      >
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-700 ease-out"
          style={{ width: isDone ? "100%" : "0%" }}
        />
      </div>

      {/* PM 카드 목록 */}
      <div className="space-y-3" aria-label="PM 추천 분석 현황">
        {isLoading
          ? Array.from({ length: displayCount }, (_, i) => (
              <PMSkeletonCard key={i} index={i} />
            ))
          : items.map((item, i) => (
              <PMReadyCard key={item.pmId} item={item} index={i} />
            ))}
      </div>

      {/* 완료 후 자동 이동 메시지 */}
      {isDone && (
        <p
          className="flex items-center justify-center gap-1.5 text-center text-xs text-emerald-500"
          aria-live="polite"
        >
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          PM 선택 화면으로 이동 중...
        </p>
      )}
    </div>
  );
}
