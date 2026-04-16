"use client";

import Link from "next/link";
import { ArrowLeft, ArrowRight, Loader2, Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  SOLUTION_WIZARD_STEPS,
  useSolutionWizardStore,
} from "@/stores/solution-wizard-store";

import { SolutionWizardStepper } from "./solution-wizard-stepper";

interface SolutionWizardLayoutProps {
  children: React.ReactNode;
  /** 마지막 스텝에서 호출되는 제출 핸들러 */
  onSubmit: () => void;
  /** 중간 스텝에서 "다음" 클릭 시 호출 (미제공 시 내부 nextStep 호출) */
  onNextStep?: () => Promise<void>;
  isSubmitting?: boolean;
  /** 현재 스텝 진행 가능 여부 */
  canProceed?: boolean;
  /** 다음 버튼 레이블 오버라이드 */
  nextLabel?: string;
}

export function SolutionWizardLayout({
  children,
  onSubmit,
  onNextStep,
  isSubmitting = false,
  canProceed = true,
  nextLabel,
}: SolutionWizardLayoutProps) {
  const { currentStep, nextStep, prevStep, isGenerating } =
    useSolutionWizardStore();

  const isFirst = currentStep === 0;
  const isLast = currentStep === SOLUTION_WIZARD_STEPS.length - 1;
  const isBlocked = isSubmitting || isGenerating;

  const handleNext = () => {
    if (isLast) {
      onSubmit();
    } else if (onNextStep) {
      void onNextStep();
    } else {
      nextStep();
    }
  };

  const defaultNextLabel = isLast ? "프로젝트 생성" : "다음";

  return (
    <div className="mx-auto max-w-3xl">
      {/* 헤더 */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">새 솔루션</h1>
          <p className="mt-1 text-sm text-slate-400">
            AI가 회사에 맞는 솔루션을 자동 설계합니다
          </p>
        </div>
        <Link
          href="/solutions"
          className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 transition-colors hover:bg-emerald-500/20"
          aria-label="솔루션 목록으로 이동"
        >
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          솔루션 목록
        </Link>
      </div>

      {/* Stepper */}
      <div className="mb-8">
        <SolutionWizardStepper />
      </div>

      {/* 스텝 콘텐츠 */}
      <section
        aria-labelledby="wizard-step-heading"
        className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 sm:p-8"
      >
        <h2
          id="wizard-step-heading"
          className="mb-1 text-lg font-semibold text-white"
        >
          {SOLUTION_WIZARD_STEPS[currentStep].label}
        </h2>
        <p className="mb-6 text-sm text-slate-400">
          {SOLUTION_WIZARD_STEPS[currentStep].description}
        </p>

        <div key={currentStep} className="animate-fade-in-up">
          {children}
        </div>
      </section>

      {/* 네비게이션 버튼 */}
      <div className="mt-6 flex items-center justify-between" role="group" aria-label="위저드 네비게이션">
        <button
          type="button"
          onClick={prevStep}
          disabled={isFirst || isBlocked}
          aria-label="이전 단계로 이동"
          className={cn(
            "flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium transition-all",
            isFirst || isBlocked
              ? "cursor-not-allowed text-slate-600"
              : "text-slate-300 hover:bg-white/5 hover:text-white",
          )}
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          이전
        </button>

        <button
          type="button"
          onClick={handleNext}
          disabled={!canProceed || isBlocked}
          aria-label={
            isLast
              ? "프로젝트 생성하기"
              : `다음 단계로 이동 (${SOLUTION_WIZARD_STEPS[currentStep + 1]?.label ?? ""})`
          }
          aria-busy={isSubmitting || isGenerating}
          className={cn(
            "group flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
            !canProceed || isBlocked
              ? "cursor-not-allowed bg-emerald-600/30 text-emerald-300/50"
              : "bg-emerald-600 text-white shadow-lg shadow-emerald-600/25 hover:bg-emerald-500",
          )}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              생성 중...
            </>
          ) : isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              분석 중...
            </>
          ) : isLast ? (
            nextLabel ?? defaultNextLabel
          ) : (
            <>
              {nextLabel ?? defaultNextLabel}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
