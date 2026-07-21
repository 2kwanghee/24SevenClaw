"use client";

import { useTranslations } from "next-intl";
import { Check } from "lucide-react";

import type { OrchestratorPhase } from "@/lib/api-client";

interface StepGroup {
  key: string;
  phases: OrchestratorPhase[];
}

const STEP_GROUPS: StepGroup[] = [
  { key: "intake", phases: ["requested"] },
  { key: "context", phases: ["decomposed"] },
  { key: "plan", phases: ["assigned"] },
  { key: "implementReview", phases: ["drafting", "reviewing", "integrating"] },
  { key: "validate", phases: ["validating"] },
  { key: "mergeComplete", phases: ["approved", "transitioning", "completed"] },
];

interface DeliveryStepperProps {
  currentPhase: OrchestratorPhase;
}

export function DeliveryStepper({ currentPhase }: DeliveryStepperProps) {
  const t = useTranslations("delivery");
  const currentGroup = STEP_GROUPS.findIndex((g) =>
    g.phases.includes(currentPhase),
  );

  return (
    <ol
      className="flex items-center overflow-x-auto pb-1"
      aria-label={t("stepper.ariaLabel")}
    >
      {STEP_GROUPS.map((group, i) => {
        const isDone = currentGroup >= 0 && i < currentGroup;
        const isCurrent = i === currentGroup;
        const isFirst = i === 0;

        return (
          <li key={group.key} className="flex flex-none items-center">
            {!isFirst && (
              <span
                className={`h-0.5 w-8 sm:w-9 ${
                  isDone || isCurrent
                    ? "bg-emerald-400 dark:bg-emerald-600"
                    : "bg-[var(--border-subtle)]"
                }`}
                aria-hidden="true"
              />
            )}
            <div className="flex items-center gap-2.5 px-1 py-1">
              <span
                className={`flex h-6 w-6 flex-none items-center justify-center rounded-full text-xs font-bold ${
                  isDone
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
                    : isCurrent
                      ? "bg-[var(--accent)] text-[var(--accent-fg)] ring-4 ring-[var(--accent-soft)]"
                      : "border border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]"
                }`}
                aria-hidden="true"
              >
                {isDone ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </span>
              <span
                className={`whitespace-nowrap text-[13px] font-semibold ${
                  isCurrent
                    ? "text-[var(--accent)]"
                    : isDone
                      ? "text-[var(--text-primary)]"
                      : "text-[var(--text-muted)]"
                }`}
              >
                {t(`stepper.${group.key}`)}
                {isCurrent && (
                  <span className="sr-only"> ({t("stepper.inProgress")})</span>
                )}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
