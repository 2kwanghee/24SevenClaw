"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  SOLUTION_WIZARD_STEPS,
  useSolutionWizardStore,
} from "@/stores/solution-wizard-store";

export function SolutionWizardStepper() {
  const { currentStep, goToStep } = useSolutionWizardStore();

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      const next = index + 1;
      if (next <= currentStep) goToStep(next);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      const prev = index - 1;
      if (prev >= 0) goToStep(prev);
    }
  };

  return (
    <nav aria-label="솔루션 위저드 진행 단계" className="w-full">
      {/* 데스크톱: 가로 스텝 */}
      <ol className="hidden items-center gap-0 md:flex">
        {SOLUTION_WIZARD_STEPS.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isClickable = index <= currentStep;

          return (
            <li key={step.id} className="flex flex-1 items-center">
              <button
                type="button"
                onClick={() => isClickable && goToStep(index)}
                onKeyDown={(e) => isClickable && handleKeyDown(e, index)}
                disabled={!isClickable}
                className={cn(
                  "group flex w-full flex-col items-center gap-2",
                  isClickable ? "cursor-pointer" : "cursor-default",
                )}
                aria-current={isCurrent ? "step" : undefined}
                aria-label={`${step.label} (${index + 1}/${SOLUTION_WIZARD_STEPS.length}단계)${isCompleted ? " - 완료됨" : isCurrent ? " - 현재 단계" : " - 미완료"}`}
              >
                <div className="flex w-full items-center">
                  {index > 0 ? (
                    <div
                      className={cn(
                        "h-0.5 flex-1 transition-colors duration-300",
                        isCompleted ? "bg-zinc-900" : "bg-zinc-200",
                      )}
                    />
                  ) : (
                    <div className="flex-1" />
                  )}

                  <div
                    className={cn(
                      "relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-semibold transition-all duration-300",
                      isCompleted
                        ? "border-zinc-900 bg-zinc-900 text-white"
                        : isCurrent
                          ? "border-zinc-900 bg-white text-zinc-900 ring-4 ring-zinc-200"
                          : "border-zinc-200 bg-white text-zinc-500",
                    )}
                  >
                    {isCompleted ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </div>

                  {index < SOLUTION_WIZARD_STEPS.length - 1 ? (
                    <div
                      className={cn(
                        "h-0.5 flex-1 transition-colors duration-300",
                        isCompleted ? "bg-zinc-900" : "bg-zinc-200",
                      )}
                    />
                  ) : (
                    <div className="flex-1" />
                  )}
                </div>

                <p
                  className={cn(
                    "text-xs font-medium transition-colors",
                    isCurrent
                      ? "font-semibold text-zinc-900"
                      : isCompleted
                        ? "text-zinc-600"
                        : "text-zinc-500",
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
        <div className="mb-3 h-1 w-full overflow-hidden rounded-full bg-zinc-200">
          <div
            className="h-full rounded-full bg-zinc-900 transition-all duration-500 ease-out"
            style={{
              width: `${((currentStep + 1) / SOLUTION_WIZARD_STEPS.length) * 100}%`,
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-900 text-xs font-semibold text-white">
              {currentStep + 1}
            </span>
            <span className="text-sm font-medium text-zinc-950">
              {SOLUTION_WIZARD_STEPS[currentStep].label}
            </span>
          </div>
          <span className="text-xs text-zinc-500">
            {currentStep + 1} / {SOLUTION_WIZARD_STEPS.length}
          </span>
        </div>
        <p className="mt-1 text-xs text-zinc-500">
          {SOLUTION_WIZARD_STEPS[currentStep].description}
        </p>
      </div>
    </nav>
  );
}
