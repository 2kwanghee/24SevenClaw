"use client";

import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { WIZARD_STEPS, useWizardStore } from "@/stores/wizard-store";

import { WizardStepper } from "./stepper";

interface WizardLayoutProps {
  children: React.ReactNode;
  /** 마지막 스텝에서 호출되는 제출 핸들러 */
  onSubmit: () => void;
  isSubmitting?: boolean;
  /** 현재 스텝의 유효성 검사 통과 여부 */
  canProceed?: boolean;
}

export function WizardLayout({
  children,
  onSubmit,
  isSubmitting = false,
  canProceed = true,
}: WizardLayoutProps) {
  const { currentStep, nextStep, prevStep } = useWizardStore();

  const isFirst = currentStep === 0;
  const isLast = currentStep === WIZARD_STEPS.length - 1;

  const handleNext = () => {
    if (isLast) {
      onSubmit();
    } else {
      nextStep();
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">새 프로젝트</h1>
        <p className="mt-1 text-sm text-slate-400">
          7단계 위저드로 AI 솔루션을 설계합니다
        </p>
      </div>

      {/* Stepper */}
      <div className="mb-8">
        <WizardStepper />
      </div>

      {/* 스텝 콘텐츠 영역 */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 sm:p-8">
        <h2 className="mb-1 text-lg font-semibold text-white">
          {WIZARD_STEPS[currentStep].label}
        </h2>
        <p className="mb-6 text-sm text-slate-400">
          {WIZARD_STEPS[currentStep].description}
        </p>

        <div
          key={currentStep}
          className="animate-fade-in-up"
        >
          {children}
        </div>
      </div>

      {/* 네비게이션 버튼 */}
      <div className="mt-6 flex items-center justify-between">
        <button
          type="button"
          onClick={prevStep}
          disabled={isFirst || isSubmitting}
          className={cn(
            "flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium transition-all",
            isFirst || isSubmitting
              ? "cursor-not-allowed text-slate-600"
              : "text-slate-300 hover:bg-white/5 hover:text-white"
          )}
        >
          <ArrowLeft className="h-4 w-4" />
          이전
        </button>

        <button
          type="button"
          onClick={handleNext}
          disabled={!canProceed || isSubmitting}
          className={cn(
            "group flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
            !canProceed || isSubmitting
              ? "cursor-not-allowed bg-violet-600/30 text-violet-300/50"
              : "bg-violet-600 text-white shadow-lg shadow-violet-600/25 hover:bg-violet-500"
          )}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              생성 중...
            </>
          ) : isLast ? (
            "프로젝트 생성"
          ) : (
            <>
              다음
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
