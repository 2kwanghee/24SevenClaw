"use client";

import { AlertCircle, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { prototypeSessions, ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { PrototypeCard } from "../prototype-card";

/** 로딩 단계 표시용 */
const LOADING_STEPS = [
  "입력 정보 분석 중...",
  "솔루션 구조 설계 중...",
  "최적 구성 완료 중...",
] as const;

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 30; // 최대 60초

interface LoadingStepItemProps {
  label: string;
  status: "pending" | "active" | "done";
}

function LoadingStepItem({ label, status }: LoadingStepItemProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 text-sm transition-all duration-300",
        status === "done" && "text-emerald-400",
        status === "active" && "text-white",
        status === "pending" && "text-slate-600",
      )}
    >
      {status === "done" ? (
        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
      ) : status === "active" ? (
        <Loader2 className="h-4 w-4 shrink-0 animate-spin text-emerald-400" />
      ) : (
        <div className="h-4 w-4 shrink-0 rounded-full border border-slate-700" />
      )}
      <span>{label}</span>
    </div>
  );
}

export function StepPrototypes() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);
  const prototypes = useSolutionWizardStore((s) => s.data.prototypes);
  const isGenerating = useSolutionWizardStore((s) => s.isGenerating);
  const selectPrototype = useSolutionWizardStore((s) => s.selectPrototype);
  const setGeneratedPrototypes = useSolutionWizardStore(
    (s) => s.setGeneratedPrototypes,
  );
  const setIsGenerating = useSolutionWizardStore((s) => s.setIsGenerating);

  const [loadingStep, setLoadingStep] = useState(0);
  const [hasFailed, setHasFailed] = useState(false);

  // 폴링 중단용 ref
  const cancelledRef = useRef(false);
  const pollCountRef = useRef(0);

  // 컴포넌트 언마운트 시 폴링 중단
  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  // 로딩 스텝 애니메이션 (1초마다 진행)
  useEffect(() => {
    if (!isGenerating) return;

    const timer = setInterval(() => {
      setLoadingStep((prev) =>
        prev < LOADING_STEPS.length - 1 ? prev + 1 : prev,
      );
    }, 1800);

    return () => clearInterval(timer);
  }, [isGenerating]);

  useEffect(() => {
    if (!sessionId || !token) return;
    if (prototypes.generatedPrototypes.length > 0) return;

    const start = async () => {
      setIsGenerating(true);
      setLoadingStep(0);
      setHasFailed(false);

      // 1) 생성 시작 (202 Accepted 또는 이미 시작됨이면 무시)
      try {
        await prototypeSessions.generate(token, sessionId);
      } catch (err) {
        if (err instanceof ApiClientError && err.status === 409) {
          // 이미 generating/completed — 그냥 폴링 계속
        } else {
          setIsGenerating(false);
          setHasFailed(true);
          return;
        }
      }

      // 2) 폴링: status가 completed 또는 failed가 될 때까지
      const poll = async () => {
        if (cancelledRef.current) return;
        pollCountRef.current += 1;

        if (pollCountRef.current > MAX_POLL_ATTEMPTS) {
          setIsGenerating(false);
          setHasFailed(true);
          return;
        }

        try {
          const statusResp = await prototypeSessions.getStatus(token, sessionId);

          if (cancelledRef.current) return;

          if (statusResp.status === "completed") {
            const protoList = await prototypeSessions.listPrototypes(
              token,
              sessionId,
            );
            if (!cancelledRef.current) {
              setGeneratedPrototypes(
                protoList.items.map((p) => ({
                  id: p.id,
                  name: p.title,
                  solutionType: p.design_pattern ?? "custom",
                  reasoning: p.description,
                  config: (p.ui_structure ?? {}) as Record<string, unknown>,
                })),
              );
              setIsGenerating(false);
            }
          } else if (statusResp.status === "failed") {
            if (!cancelledRef.current) {
              setIsGenerating(false);
              setHasFailed(true);
            }
          } else {
            // 아직 generating/pending — 다음 폴링 예약
            setTimeout(() => void poll(), POLL_INTERVAL_MS);
          }
        } catch {
          if (!cancelledRef.current) {
            setTimeout(() => void poll(), POLL_INTERVAL_MS);
          }
        }
      };

      setTimeout(() => void poll(), POLL_INTERVAL_MS);
    };

    void start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, token]);

  /* ── 로딩 상태 ─────────────────────────────────── */
  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        {/* 애니메이션 아이콘 */}
        <div className="relative mb-6">
          <div className="h-20 w-20 rounded-full border border-emerald-500/20 bg-emerald-500/5 animate-pulse" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Sparkles className="h-8 w-8 text-emerald-400 animate-pulse" />
          </div>
        </div>

        <h3 className="mb-1 text-sm font-semibold text-white">
          AI가 솔루션을 설계하고 있습니다
        </h3>
        <p className="mb-8 text-xs text-slate-500">
          입력하신 정보를 분석하여 최적의 아키텍처를 구성 중입니다
        </p>

        {/* 단계별 진행 표시 */}
        <div className="w-full max-w-xs space-y-3">
          {LOADING_STEPS.map((label, idx) => (
            <LoadingStepItem
              key={label}
              label={label}
              status={
                idx < loadingStep
                  ? "done"
                  : idx === loadingStep
                    ? "active"
                    : "pending"
              }
            />
          ))}
        </div>
      </div>
    );
  }

  /* ── 실패 상태 ─────────────────────────────────── */
  if (hasFailed) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertCircle className="h-10 w-10 text-rose-500" />
        <p className="mt-4 text-sm font-medium text-rose-400">
          프로토타입 생성에 실패했습니다
        </p>
        <p className="mt-1 text-xs text-slate-500">
          이전 단계로 돌아가 정보를 다시 확인해 주세요
        </p>
      </div>
    );
  }

  /* ── 빈 상태 (세션 없음) ───────────────────────── */
  if (prototypes.generatedPrototypes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Sparkles className="h-10 w-10 text-slate-600" />
        <p className="mt-4 text-sm text-slate-400">
          프로토타입을 생성할 수 없습니다
        </p>
        <p className="mt-1 text-xs text-slate-500">
          이전 단계로 돌아가 정보를 다시 확인해 주세요
        </p>
      </div>
    );
  }

  /* ── 프로토타입 카드 목록 ──────────────────────── */
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400">
        AI가 분석한 솔루션 후보입니다. 가장 적합한 방향을 선택하세요.
      </p>
      <div className="space-y-3">
        {prototypes.generatedPrototypes.map((proto) => (
          <PrototypeCard
            key={proto.id}
            prototype={proto}
            isSelected={prototypes.selectedPrototypeId === proto.id}
            onSelect={selectPrototype}
          />
        ))}
      </div>
    </div>
  );
}
