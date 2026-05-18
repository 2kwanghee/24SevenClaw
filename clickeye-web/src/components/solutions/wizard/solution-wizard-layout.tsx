"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useRef } from "react";
import { ArrowLeft, ArrowRight, Loader2, Sparkles, HelpCircle, PanelRightOpen } from "lucide-react";

import { cn } from "@/lib/utils";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { getWizardSteps, type SolutionWizardMode } from "@/types/solution-wizard";

import { SolutionWizardStepper } from "./solution-wizard-stepper";
import { WizardArtifactPanel } from "./artifact-panel/wizard-artifact-panel";

const WizardTourWrapper = dynamic(
  () =>
    import("@/components/onboarding/wizard-tour").then((m) => ({
      default: m.WizardTourWrapper,
    })),
  { ssr: false },
);

interface SolutionWizardLayoutProps {
  children: React.ReactNode;
  /** 마지막 스텝에서 호출되는 제출 핸들러 */
  onSubmit?: () => void;
  /** 중간 스텝에서 "다음" 클릭 시 호출 (미제공 시 내부 nextStep 호출) */
  onNextStep?: () => Promise<void>;
  isSubmitting?: boolean;
  /** 현재 스텝 진행 가능 여부 */
  canProceed?: boolean;
  /** 다음 버튼 레이블 오버라이드 */
  nextLabel?: string;
  /**
   * 위저드 모드 — 'new' (기본, 기존 솔루션 위저드) / 'modernize' (기존 코드 현대화).
   * 기본값 'new'. 기존 호출자는 mode 를 모르더라도 'new' 동작 유지.
   */
  mode?: SolutionWizardMode;
  /** currentStep override — 미지정 시 store 의 currentStep 사용 */
  currentStep?: number;
}

export function SolutionWizardLayout({
  children,
  onSubmit,
  onNextStep,
  isSubmitting = false,
  canProceed = true,
  nextLabel,
  mode = "new",
  currentStep: currentStepProp,
}: SolutionWizardLayoutProps) {
  const {
    currentStep: storeCurrentStep,
    nextStep,
    prevStep,
    isGenerating,
    togglePreviewPanel,
  } = useSolutionWizardStore();
  const { restartWizardTour } = useOnboardingStore();

  const currentStep = currentStepProp ?? storeCurrentStep;

  const stepHeadingRef = useRef<HTMLHeadingElement>(null);

  // 스텝 전환 시 스텝 제목으로 포커스 이동
  useEffect(() => {
    stepHeadingRef.current?.focus();
  }, [currentStep]);

  // mode 에 따라 적절한 step 배열 사용. mode='new' 일 때 기존 SOLUTION_WIZARD_STEPS 와 동일.
  const steps = getWizardSteps(mode);
  const isFirst = currentStep === 0;
  const isLast = currentStep === steps.length - 1;
  const isBlocked = isSubmitting || isGenerating;

  const handleNext = () => {
    if (isLast) {
      onSubmit?.();
    } else if (onNextStep) {
      void onNextStep();
    } else {
      nextStep();
    }
  };

  const defaultNextLabel = isLast ? "이대로 진행" : "다음";

  return (
    <div className="mx-auto max-w-[1280px]">
      {/* 위저드 온보딩 투어 (SSR 비활성화, 첫 방문 시 자동 시작) */}
      <WizardTourWrapper />
      {/* 모바일 프리뷰 패널 (sheet 모드 — xl 미만에서만 렌더) */}
      <WizardArtifactPanel sheetMode />

      {/* 헤더 */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-950">
            {mode === "modernize" ? "기존 코드 현대화" : "새 솔루션"}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            {mode === "modernize"
              ? "GitHub repo 를 연결하면 AI 가 코드를 진단하고 현대화 작업을 자동 등록합니다"
              : "AI가 회사에 맞는 솔루션을 자동 설계합니다"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* 모바일 프리뷰 토글 버튼 (xl 미만에서만 표시) */}
          <button
            type="button"
            onClick={togglePreviewPanel}
            aria-label="라이브 프리뷰 열기"
            title="라이브 프리뷰"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 xl:hidden"
          >
            <PanelRightOpen className="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={restartWizardTour}
            aria-label="위저드 가이드 다시 보기"
            title="위저드 가이드 다시 보기"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
          >
            <HelpCircle className="h-4 w-4" aria-hidden="true" />
          </button>
          <Link
            href="/solutions"
            className="flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-100"
            aria-label="솔루션 목록으로 이동"
          >
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            솔루션 목록
          </Link>
        </div>
      </div>

      {/* Stepper */}
      <div className="mb-8" data-tour="wizard-stepper">
        <SolutionWizardStepper steps={steps} currentStep={currentStep} />
      </div>

      {/* 메인 영역 — 데스크탑(xl+): 폼(좌) + 프리뷰 패널(우) split view */}
      <div className="xl:grid xl:grid-cols-[minmax(0,1fr)_380px] xl:items-start xl:gap-6">
        {/* 좌측: 폼 + 네비게이션 */}
        <div>
          {/* 스텝 콘텐츠 */}
          <section
            aria-labelledby="wizard-step-heading"
            data-tour="wizard-content"
            className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:p-8"
          >
            <h2
              id="wizard-step-heading"
              ref={stepHeadingRef}
              tabIndex={-1}
              className="mb-1 text-lg font-semibold text-zinc-950 outline-none"
            >
              {steps[currentStep]?.label ?? ""}
            </h2>
            <p className="mb-6 text-sm text-zinc-500">
              {steps[currentStep]?.description ?? ""}
            </p>

            <div key={currentStep} className="animate-fade-in-up">
              {children}
            </div>
          </section>

          {/* 네비게이션 버튼 */}
          <div
            className="mt-6 flex items-center justify-between"
            role="group"
            aria-label="위저드 네비게이션"
            data-tour="wizard-nav"
          >
            <button
              type="button"
              onClick={prevStep}
              disabled={isFirst || isBlocked}
              aria-label="이전 단계로 이동"
              className={cn(
                "flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium transition-all",
                isFirst || isBlocked
                  ? "cursor-not-allowed text-zinc-300"
                  : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900",
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
                  : `다음 단계로 이동 (${steps[currentStep + 1]?.label ?? ""})`
              }
              aria-busy={isSubmitting || isGenerating}
              className={cn(
                "group flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
                !canProceed || isBlocked
                  ? "cursor-not-allowed bg-zinc-200 text-zinc-400"
                  : "bg-zinc-900 text-white shadow-sm hover:bg-zinc-800",
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

        {/* 우측: 라이브 프리뷰 패널 (xl+ 에서만 표시) */}
        <WizardArtifactPanel />
      </div>
    </div>
  );
}
