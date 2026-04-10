"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import { WIZARD_STEPS, useWizardStore } from "@/stores/wizard-store";

export function WizardStepper() {
  const { currentStep, goToStep } = useWizardStore();

  return (
    <nav aria-label="위저드 진행 단계" className="w-full">
      {/* 데스크톱: 가로 스텝 */}
      <ol className="hidden items-center gap-0 md:flex">
        {WIZARD_STEPS.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isClickable = index <= currentStep;

          return (
            <li key={step.id} className="flex flex-1 items-center">
              <button
                type="button"
                onClick={() => isClickable && goToStep(index)}
                disabled={!isClickable}
                className={cn(
                  "group flex w-full flex-col items-center gap-2",
                  isClickable ? "cursor-pointer" : "cursor-default",
                )}
                aria-current={isCurrent ? "step" : undefined}
              >
                {/* 커넥터 + 원형 인디케이터 */}
                <div className="flex w-full items-center">
                  {/* 좌측 커넥터 */}
                  {index > 0 ? (
                    <div
                      className={cn(
                        "h-0.5 flex-1 transition-colors duration-300",
                        isCompleted ? "bg-violet-500" : "bg-white/10",
                      )}
                    />
                  ) : (
                    <div className="flex-1" />
                  )}

                  {/* 원형 인디케이터 */}
                  <div
                    className={cn(
                      "relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-semibold transition-all duration-300",
                      isCompleted
                        ? "border-violet-500 bg-violet-500 text-white"
                        : isCurrent
                          ? "border-violet-500 bg-violet-500/10 text-violet-300 ring-4 ring-violet-500/20"
                          : "border-white/10 bg-white/[0.02] text-slate-500",
                    )}
                  >
                    {isCompleted ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </div>

                  {/* 우측 커넥터 */}
                  {index < WIZARD_STEPS.length - 1 ? (
                    <div
                      className={cn(
                        "h-0.5 flex-1 transition-colors duration-300",
                        isCompleted ? "bg-violet-500" : "bg-white/10",
                      )}
                    />
                  ) : (
                    <div className="flex-1" />
                  )}
                </div>

                {/* 라벨 */}
                <p
                  className={cn(
                    "text-xs font-medium transition-colors",
                    isCurrent
                      ? "text-violet-300"
                      : isCompleted
                        ? "text-slate-300"
                        : "text-slate-500",
                  )}
                >
                  {step.label}
                </p>
              </button>
            </li>
          );
        })}
      </ol>

      {/* 모바일: 압축 스텝 */}
      <div className="md:hidden">
        {/* 진행률 바 */}
        <div className="mb-3 h-1 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-violet-500 transition-all duration-500 ease-out"
            style={{
              width: `${((currentStep + 1) / WIZARD_STEPS.length) * 100}%`,
            }}
          />
        </div>

        {/* 현재 단계 표시 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-violet-500/10 text-xs font-semibold text-violet-300">
              {currentStep + 1}
            </span>
            <span className="text-sm font-medium text-white">
              {WIZARD_STEPS[currentStep].label}
            </span>
          </div>
          <span className="text-xs text-slate-500">
            {currentStep + 1} / {WIZARD_STEPS.length}
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {WIZARD_STEPS[currentStep].description}
        </p>
      </div>
    </nav>
  );
}
