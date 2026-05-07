"use client";

import { Sparkles, X, AlertCircle } from "lucide-react";

import { useSolutionWizardStore, SOLUTION_WIZARD_STEPS } from "@/stores/solution-wizard-store";
import type { SolutionWizardStepId } from "@/types/solution-wizard";

import { ArtifactSkeleton } from "./artifact-skeleton";
import { CompanyBlueprintView } from "./views/company-blueprint-view";

function StepArtifact({
  stepId,
  result,
}: {
  stepId: SolutionWizardStepId;
  result: Record<string, unknown>;
}) {
  if (stepId === "company") {
    return <CompanyBlueprintView result={result} />;
  }
  return null;
}

const STEP_DESCRIPTIONS: Partial<Record<SolutionWizardStepId, string>> = {
  company: "입력 내용을 분석해 솔루션 청사진을 실시간으로 보여줍니다",
  generation: "솔루션 생성이 완료되면 여기에 요약이 나타납니다",
  prototypes: "프로토타입을 선택하면 아키텍처 구조가 나타납니다",
  "pm-recommendation": "PM 추천 결과가 여기에 나타납니다",
  "pm-selection": "선택한 PM의 매칭 점수가 여기에 나타납니다",
  "pm-composition": "PM 구성요소 요약이 여기에 나타납니다",
  agents: "에이전트 구성 요약이 여기에 나타납니다",
  platform: "플랫폼 비교 정보가 여기에 나타납니다",
  os: "실행 환경 정보가 여기에 나타납니다",
  env: "필요한 환경변수 체크리스트가 여기에 나타납니다",
  roi: "ROI 비교 차트가 여기에 나타납니다",
  confirm: "최종 솔루션 요약이 여기에 나타납니다",
};

interface WizardArtifactPanelProps {
  /** 모바일 sheet 모드 — true이면 overlay/시트 스타일 */
  sheetMode?: boolean;
}

export function WizardArtifactPanel({ sheetMode = false }: WizardArtifactPanelProps) {
  const {
    currentStep,
    previewByStep,
    previewLoadingStep,
    previewErrorByStep,
    previewPanelOpen,
    togglePreviewPanel,
  } = useSolutionWizardStore();

  const stepDef = SOLUTION_WIZARD_STEPS[currentStep];
  const stepId = stepDef?.id as SolutionWizardStepId;
  const result = previewByStep[stepId];
  const isLoading = previewLoadingStep === stepId;
  const error = previewErrorByStep[stepId];
  const description = STEP_DESCRIPTIONS[stepId];

  if (sheetMode && !previewPanelOpen) return null;

  return (
    <>
      {/* 모바일 오버레이 배경 */}
      {sheetMode && (
        <div
          className="fixed inset-0 z-40 bg-black/40 xl:hidden"
          onClick={togglePreviewPanel}
          aria-hidden="true"
        />
      )}

      <aside
        aria-label="솔루션 청사진 프리뷰"
        className={
          sheetMode
            ? "fixed bottom-0 left-0 right-0 z-50 rounded-t-2xl border-t border-zinc-200 bg-white shadow-2xl xl:hidden"
            : "hidden xl:block"
        }
      >
        <div
          className={`flex flex-col gap-4 ${
            sheetMode ? "max-h-[70vh] overflow-y-auto p-6" : "sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto rounded-2xl border border-zinc-200 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
          }`}
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-500" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-zinc-900">라이브 프리뷰</h3>
            </div>
            {sheetMode && (
              <button
                type="button"
                onClick={togglePreviewPanel}
                aria-label="프리뷰 닫기"
                className="rounded-lg p-1 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>

          {/* 단계 이름 */}
          <div>
            <p className="text-xs font-medium text-zinc-700">{stepDef?.label}</p>
            {description && (
              <p className="mt-0.5 text-xs text-zinc-400">{description}</p>
            )}
          </div>

          <div className="h-px bg-zinc-100" />

          {/* 컨텐츠 */}
          {isLoading ? (
            <ArtifactSkeleton />
          ) : error ? (
            <div className="flex items-start gap-2 rounded-lg border border-red-100 bg-red-50 p-3">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" aria-hidden="true" />
              <p className="text-xs text-red-600">{error}</p>
            </div>
          ) : result ? (
            <StepArtifact stepId={stepId} result={result} />
          ) : (
            <p className="text-xs text-zinc-400">
              {description ?? "입력을 시작하면 프리뷰가 나타납니다."}
            </p>
          )}
        </div>
      </aside>
    </>
  );
}
