"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { prototypeSessions, ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/* -- 상수 -------------------------------------------------------------- */

const EXPECTED_COUNT = 3;
const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 40; // 최대 2분
const REVEAL_STAGGER_MS = 350;

/* -- 타입 -------------------------------------------------------------- */

type CardStatus = "skeleton" | "generating" | "ready";

interface PrototypeCardItem {
  id: string;
  name: string;
  description: string | null;
  solutionType: string;
  status: CardStatus;
}

/* -- 하위 컴포넌트 ----------------------------------------------------- */

function SkeletonCard({ index }: { index: number }) {
  return (
    <div
      className="animate-pulse rounded-xl border border-zinc-200 bg-zinc-50 p-4"
      style={{ animationDelay: `${index * 120}ms` }}
      aria-hidden="true"
    >
      <div className="mb-3 flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-zinc-100" />
        <div className="h-4 w-36 rounded-md bg-zinc-100" />
      </div>
      <div className="space-y-2">
        <div className="h-3 w-full rounded-md bg-zinc-100" />
        <div className="h-3 w-4/5 rounded-md bg-zinc-100" />
        <div className="h-3 w-3/5 rounded-md bg-zinc-100" />
      </div>
      <div className="mt-3 flex gap-2">
        <div className="h-5 w-16 rounded-full bg-zinc-100" />
        <div className="h-5 w-20 rounded-full bg-zinc-100" />
      </div>
    </div>
  );
}

interface GeneratingCardProps {
  index: number;
  ariaLabel: string;
}

function GeneratingCard({ index, ariaLabel }: GeneratingCardProps) {
  return (
    <div
      className="rounded-xl border border-emerald-200 bg-emerald-50 p-4"
      style={{ animationDelay: `${index * 120}ms` }}
      aria-label={ariaLabel}
    >
      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-50">
          <Loader2 className="h-4 w-4 animate-spin text-emerald-600" aria-hidden="true" />
        </div>
        <div className="h-4 w-36 animate-pulse rounded-md bg-zinc-100" />
      </div>
      <div className="space-y-2">
        <div className="h-3 w-full animate-pulse rounded-md bg-zinc-100" />
        <div className="h-3 w-4/5 animate-pulse rounded-md bg-zinc-100" />
      </div>
    </div>
  );
}

interface ReadyCardProps {
  card: PrototypeCardItem;
  index: number;
  ariaLabel: string;
}

function ReadyCard({ card, index, ariaLabel }: ReadyCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-emerald-200 bg-emerald-50 p-4",
        "transition-all duration-500",
        "animate-in fade-in slide-in-from-bottom-2",
      )}
      style={{ animationDelay: `${index * 80}ms`, animationDuration: "400ms" }}
      role="status"
      aria-label={ariaLabel}
    >
      <div className="mb-2 flex items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-50">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
        </div>
        <h3 className="text-sm font-semibold text-zinc-950">{card.name}</h3>
      </div>
      {card.description && (
        <p className="mb-2.5 line-clamp-2 text-xs leading-relaxed text-zinc-500">
          {card.description}
        </p>
      )}
      <span className="inline-block rounded-full border border-emerald-500/20 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-600">
        {card.solutionType}
      </span>
    </div>
  );
}

/* -- 메인 컴포넌트 ----------------------------------------------------- */

export function StepPrototypeGeneration() {
  const t = useTranslations("wizard.step2");
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);
  const existingPrototypes = useSolutionWizardStore(
    (s) => s.data.prototypes.generatedPrototypes,
  );
  const setGeneratedPrototypes = useSolutionWizardStore(
    (s) => s.setGeneratedPrototypes,
  );
  const setIsGenerating = useSolutionWizardStore((s) => s.setIsGenerating);
  const setStep1Done = useSolutionWizardStore((s) => s.setStep1Done);

  const [cards, setCards] = useState<PrototypeCardItem[]>([]);
  const [readyCount, setReadyCount] = useState(0);
  const [isStarting, setIsStarting] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [isDisabledByAdmin, setIsDisabledByAdmin] = useState(false);

  const cancelledRef = useRef(false);
  const pollCountRef = useRef(0);
  // StrictMode에서 동일 sessionId에 대해 중복 호출을 막기 위해 ref에 sessionId를 저장
  const startedSessionRef = useRef<string | null>(null);

  /* -- 생성 실행 -- */
  const startGeneration = useCallback(async () => {
    if (!sessionId || !token) return;
    // 동일 sessionId로 이미 시작한 경우 StrictMode 이중 실행 방지
    if (startedSessionRef.current === sessionId) return;
    startedSessionRef.current = sessionId;

    cancelledRef.current = false;
    pollCountRef.current = 0;

    setIsStarting(true);
    setIsGenerating(true);
    setIsFailed(false);
    setIsDisabledByAdmin(false);
    setReadyCount(0);
    setCards([]);

    // 1) 생성 트리거
    try {
      await prototypeSessions.generatePrototypes(token, sessionId);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 409) {
        // 이미 generating/completed — 폴링만 계속
      } else if (err instanceof ApiClientError && err.status === 503) {
        setIsGenerating(false);
        setIsDisabledByAdmin(true);
        setIsStarting(false);
        return;
      } else {
        setIsGenerating(false);
        setIsFailed(true);
        setIsStarting(false);
        return;
      }
    }
    setIsStarting(false);

    // 2) 상태 폴링
    const poll = async () => {
      if (cancelledRef.current) return;
      pollCountRef.current += 1;

      if (pollCountRef.current > MAX_POLL_ATTEMPTS) {
        setIsGenerating(false);
        setIsFailed(true);
        return;
      }

      try {
        const statusResp = await prototypeSessions.getStatus(token, sessionId);
        if (cancelledRef.current) return;

        if (statusResp.status === "completed") {
          // 3) 프로토타입 목록 가져오기
          const protoList = await prototypeSessions.getPrototypes(
            token,
            sessionId,
          );
          if (cancelledRef.current) return;

          // variant_index 기준 dedup: race condition으로 동일 variant_index의 중복 행이 생길 수 있음
          const uniqueItems = Array.from(
            new Map(protoList.items.map((p) => [p.variant_index, p])).values()
          );
          const fetched: PrototypeCardItem[] = uniqueItems.map((p) => ({
            id: p.id,
            name: p.title,
            description: p.description,
            solutionType: p.design_pattern ?? "custom",
            status: "generating",
          }));

          setCards(fetched);

          // 스토어에 저장
          setGeneratedPrototypes(
            uniqueItems.map((p) => ({
              id: p.id,
              name: p.title,
              solutionType: p.design_pattern ?? "custom",
              reasoning: p.description,
              config: (p.ui_structure ?? {}) as Record<string, unknown>,
              techStack: Array.isArray(p.tech_stack_tags) ? p.tech_stack_tags : [],
              architecturePattern: p.architecture_pattern ?? undefined,
              rationale: p.variant_rationale ?? undefined,
              isRecommended: p.is_recommended,
              pros: Array.isArray(p.pros) ? p.pros : [],
              cons: Array.isArray(p.cons) ? p.cons : [],
              // 정량 지표 (Phase A)
              estimatedWeeksMin: p.estimated_weeks_min ?? null,
              estimatedWeeksMax: p.estimated_weeks_max ?? null,
              teamSizeMin: p.team_size_min ?? null,
              teamSizeMax: p.team_size_max ?? null,
              teamRoles: p.team_roles ?? [],
              complexityScore: p.complexity_score ?? null,
              scalabilityScore: p.scalability_score ?? null,
              monthlyCostMinUsd: p.monthly_cost_min_usd ?? null,
              monthlyCostMaxUsd: p.monthly_cost_max_usd ?? null,
              maintenanceDifficulty: p.maintenance_difficulty ?? null,
              skillRequirements: p.skill_requirements ?? [],
              matchReasoning: p.match_reasoning ?? null,
            })),
          );

          // 4) 순차 카드 공개 (stagger)
          for (let i = 0; i < fetched.length; i++) {
            await new Promise<void>((res) =>
              setTimeout(res, REVEAL_STAGGER_MS),
            );
            if (cancelledRef.current) return;
            setCards((prev) =>
              prev.map((c, idx) =>
                idx === i ? { ...c, status: "ready" } : c,
              ),
            );
            setReadyCount(i + 1);
          }

          setIsGenerating(false);

          // 5) 완료 플래그 설정 → 부모의 canProceed(case 1)가 true가 되어 "다음" 버튼 활성화
          if (!cancelledRef.current) {
            setStep1Done(true);
          }
        } else if (statusResp.status === "failed") {
          setIsGenerating(false);
          setIsFailed(true);
        } else {
          // pending / generating — 다음 폴링 예약
          setTimeout(() => void poll(), POLL_INTERVAL_MS);
        }
      } catch {
        if (!cancelledRef.current) {
          setTimeout(() => void poll(), POLL_INTERVAL_MS);
        }
      }
    };

    setTimeout(() => void poll(), POLL_INTERVAL_MS);
  }, [sessionId, token, setGeneratedPrototypes, setIsGenerating, setStep1Done]);

  /* -- 이미 생성된 프로토타입이 있으면 카드 복원 + 다음 버튼 활성화 -- */
  useEffect(() => {
    if (existingPrototypes.length > 0) {
      const readyCards: PrototypeCardItem[] = existingPrototypes.map((p) => ({
        id: p.id,
        name: p.name,
        description: p.reasoning,
        solutionType: p.solutionType,
        status: "ready" as CardStatus,
      }));
      setCards(readyCards);
      setReadyCount(readyCards.length);
      setIsGenerating(false);
      setStep1Done(true);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* -- 마운트 시 생성 시작 -- */
  useEffect(() => {
    // 이미 생성된 프로토타입이 있으면 실행 안 함 (첫 번째 effect가 처리)
    // existingPrototypes.length를 dep에 넣으면 setGeneratedPrototypes() 호출 시
    // 클린업이 실행되어 cancelledRef.current = true 가 되고
    // nextStep() 호출이 차단되는 버그 발생 → dep에서 제외
    if (existingPrototypes.length > 0) return;

    cancelledRef.current = false;
    void startGeneration();
    return () => {
      cancelledRef.current = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startGeneration]);

  /* -- 재시도 -- */
  const handleRetry = () => {
    startedSessionRef.current = null; // 동일 sessionId라도 재시작 허용
    pollCountRef.current = 0;
    void startGeneration();
  };

  const totalCount = Math.max(cards.length || EXPECTED_COUNT, EXPECTED_COUNT);

  /* -- 관리자 비활성화 상태 ------------------------------------------- */
  if (isDisabledByAdmin) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-amber-500/20 bg-amber-500/10">
          <AlertCircle
            className="h-7 w-7 text-amber-400"
            aria-hidden="true"
          />
        </div>
        <h3 className="mb-1 text-sm font-semibold text-amber-700">
          {t("disabled.title")}
        </h3>
        <p className="mb-2 text-xs text-zinc-500 max-w-xs">
          {t("disabled.description")}
        </p>
        <p className="text-xs text-zinc-400">
          {t("disabled.contactAdmin")}
        </p>
      </div>
    );
  }

  /* -- 실패 상태 ------------------------------------------------------- */
  if (isFailed) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-rose-500/20 bg-rose-500/10">
          <AlertCircle
            className="h-7 w-7 text-rose-400"
            aria-hidden="true"
          />
        </div>
        <h3 className="mb-1 text-sm font-semibold text-rose-300">
          {t("failed.title")}
        </h3>
        <p className="mb-6 text-xs text-zinc-500">
          {t("failed.description")}
        </p>
        <button
          type="button"
          onClick={handleRetry}
          className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-5 py-2.5 text-sm font-medium text-zinc-700 transition-all hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-950"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          {t("failed.retry")}
        </button>
      </div>
    );
  }

  /* -- 생성 중 + 완료 상태 ------------------------------------------- */
  const displayCards: PrototypeCardItem[] =
    cards.length > 0
      ? cards
      : Array.from({ length: EXPECTED_COUNT }, (_, i) => ({
          id: `skeleton-${i}`,
          name: "",
          description: null,
          solutionType: "",
          status: "skeleton" as CardStatus,
        }));

  const allReady = readyCount === totalCount && totalCount > 0 && !isStarting;

  return (
    <div className="space-y-6">
      {/* 헤더 + 카운터 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {isStarting ? (
            <Loader2
              className="h-5 w-5 animate-spin text-emerald-600"
              aria-hidden="true"
            />
          ) : allReady ? (
            <CheckCircle2
              className="h-5 w-5 text-emerald-600"
              aria-hidden="true"
            />
          ) : (
            <Sparkles
              className="h-5 w-5 animate-pulse text-emerald-600"
              aria-hidden="true"
            />
          )}
          <span className="text-sm font-medium text-zinc-700">
            {isStarting
              ? t("starting")
              : allReady
                ? t("completed")
                : t("generating")}
          </span>
        </div>

        <span
          className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs font-medium text-zinc-500"
          aria-live="polite"
          aria-label={t("counterAriaLabel", { total: totalCount, ready: readyCount })}
        >
          {readyCount} / {totalCount}
        </span>
      </div>

      {/* 전체 진행률 바 */}
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-100"
        role="progressbar"
        aria-valuenow={readyCount}
        aria-valuemin={0}
        aria-valuemax={totalCount}
        aria-label={t("progressAriaLabel")}
      >
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-700 ease-out"
          style={{
            width: `${totalCount > 0 ? (readyCount / totalCount) * 100 : 0}%`,
          }}
        />
      </div>

      {/* 프로토타입 카드 목록 */}
      <div className="space-y-3" aria-label={t("listAriaLabel")}>
        {displayCards.map((card, idx) =>
          card.status === "skeleton" ? (
            <SkeletonCard key={card.id} index={idx} />
          ) : card.status === "generating" ? (
            <GeneratingCard
              key={card.id}
              index={idx}
              ariaLabel={t("cardGeneratingAriaLabel")}
            />
          ) : (
            <ReadyCard
              key={card.id}
              card={card}
              index={idx}
              ariaLabel={t("cardReadyAriaLabel", { name: card.name })}
            />
          ),
        )}
      </div>

      {/* 안내 메시지 */}
      {!isStarting && !allReady && (
        <p className="text-center text-xs text-zinc-500">
          {t("waitingHint")}
        </p>
      )}

      {/* 완료 후 안내 메시지 */}
      {allReady && (
        <p className="text-center text-xs text-emerald-600">
          {t.rich("doneHint", {
            strong: (chunks) => <strong>{chunks}</strong>,
          })}
        </p>
      )}
    </div>
  );
}
