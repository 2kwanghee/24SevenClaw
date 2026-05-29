"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Sparkles, X, ChevronDown, ChevronUp, AlertCircle } from "lucide-react";

import { useSolutionWizardStore, SOLUTION_WIZARD_STEPS } from "@/stores/solution-wizard-store";
import type { SolutionWizardStepId } from "@/types/solution-wizard";

import { ArtifactSkeleton } from "./artifact-skeleton";
import { CompanyBlueprintView } from "./views/company-blueprint-view";
import { StepSummaryView } from "./views/step-summary-view";

// 아코디언에 표시할 단계 (generation, pm-recommendation 제외)
const ACCORDION_STEP_IDS: SolutionWizardStepId[] = [
  "company",
  "prototypes",
  "pm-selection",
  "pm-composition",
  "agents",
  "platform",
  "os",
  "env",
  "roi",
  "confirm",
];

// stepId → SOLUTION_WIZARD_STEPS 배열 인덱스
const STEP_INDEX: Record<string, number> = Object.fromEntries(
  SOLUTION_WIZARD_STEPS.map((s, i) => [s.id, i]),
);

function CurrentStepContent({ stepId }: { stepId: SolutionWizardStepId }) {
  const { previewByStep, previewLoadingStep, previewErrorByStep } =
    useSolutionWizardStore();
  const t = useTranslations("wizard.preview");

  if (stepId !== "company") {
    return (
      <p className="text-xs text-zinc-400">
        {t("emptyStepSummary")}
      </p>
    );
  }

  const result = previewByStep.company;
  const isLoading = previewLoadingStep === "company";
  const error = previewErrorByStep.company;

  if (isLoading) return <ArtifactSkeleton />;
  if (error) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-red-100 bg-red-50 p-3">
        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" aria-hidden="true" />
        <p className="text-xs text-red-600">{error}</p>
      </div>
    );
  }
  if (result) return <CompanyBlueprintView result={result} />;
  return (
    <p className="text-xs text-zinc-400">
      {t("emptyBlueprint")}
    </p>
  );
}

interface WizardArtifactPanelProps {
  sheetMode?: boolean;
}

export function WizardArtifactPanel({ sheetMode = false }: WizardArtifactPanelProps) {
  const { currentStep, data, previewByStep, previewPanelOpen, togglePreviewPanel } =
    useSolutionWizardStore();
  const t = useTranslations("wizard.preview");
  const tShell = useTranslations("wizard.shell");

  const currentStepId = SOLUTION_WIZARD_STEPS[currentStep]?.id as SolutionWizardStepId;
  const currentAccordionId = (ACCORDION_STEP_IDS as string[]).includes(currentStepId)
    ? currentStepId
    : null;

  // 확장 상태 — 현재 단계는 항상 포함, 완료 단계는 사용자 토글로 변경
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    new Set(currentAccordionId ? [currentAccordionId] : []),
  );

  useEffect(() => {
    if (currentAccordionId) {
      setExpandedIds((prev) => new Set([...prev, currentAccordionId]));
    }
  }, [currentAccordionId]);

  // currentStep 이상에 해당하는 accordion step만 표시
  const visibleSteps = ACCORDION_STEP_IDS.filter(
    (id) => currentStep >= (STEP_INDEX[id] ?? 999),
  );

  const toggleExpand = (stepId: string) => {
    if (stepId === currentAccordionId) return;
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  };

  if (sheetMode && !previewPanelOpen) return null;

  return (
    <>
      {sheetMode && (
        <div
          className="fixed inset-0 z-40 bg-black/40 xl:hidden"
          onClick={togglePreviewPanel}
          aria-hidden="true"
        />
      )}

      <aside
        aria-label={t("panelAria")}
        className={
          sheetMode
            ? "fixed bottom-0 left-0 right-0 z-50 rounded-t-2xl border-t border-zinc-200 bg-white shadow-2xl xl:hidden"
            : "hidden xl:block"
        }
      >
        <div
          className={
            sheetMode
              ? "max-h-[70vh] overflow-y-auto"
              : "sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto rounded-2xl border border-zinc-200 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
          }
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-500" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-zinc-900">{t("title")}</h3>
            </div>
            {sheetMode && (
              <button
                type="button"
                onClick={togglePreviewPanel}
                aria-label={t("closeAria")}
                className="rounded-lg p-1 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>

          {/* 아코디언 섹션 목록 */}
          {visibleSteps.length === 0 ? (
            <p className="p-4 text-xs text-zinc-400">
              {t("emptyPanel")}
            </p>
          ) : (
            <div className="divide-y divide-zinc-100">
              {visibleSteps.map((stepId) => {
                const stepDef = SOLUTION_WIZARD_STEPS.find((s) => s.id === stepId);
                const isCurrent = stepId === currentAccordionId;
                const isExpanded = expandedIds.has(stepId);

                return (
                  <div key={stepId}>
                    {/* 섹션 헤더 */}
                    <button
                      type="button"
                      onClick={() => toggleExpand(stepId)}
                      disabled={isCurrent}
                      aria-expanded={isExpanded}
                      className={`flex w-full items-center justify-between px-4 py-3 text-left transition-colors disabled:cursor-default ${
                        isCurrent ? "" : "hover:bg-zinc-50"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {isCurrent ? (
                          <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-amber-100">
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
                          </span>
                        ) : (
                          <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-emerald-100">
                            <svg
                              className="h-2.5 w-2.5 text-emerald-600"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth={2}
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              viewBox="0 0 12 12"
                              aria-hidden="true"
                            >
                              <polyline points="2,6 5,9 10,3" />
                            </svg>
                          </span>
                        )}
                        <span
                          className={`text-xs font-medium ${
                            isCurrent ? "text-zinc-900" : "text-zinc-600"
                          }`}
                        >
                          {stepDef ? tShell(`steps.${stepDef.id}.label`) : ""}
                        </span>
                      </div>
                      {!isCurrent && (
                        isExpanded ? (
                          <ChevronUp className="h-3.5 w-3.5 shrink-0 text-zinc-400" aria-hidden="true" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-zinc-400" aria-hidden="true" />
                        )
                      )}
                    </button>

                    {/* 섹션 콘텐츠 */}
                    {isExpanded && (
                      <div className="px-4 pb-4">
                        {isCurrent ? (
                          <CurrentStepContent stepId={stepId} />
                        ) : (
                          <StepSummaryView
                            stepId={stepId}
                            data={data}
                            previewByStep={previewByStep}
                          />
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
