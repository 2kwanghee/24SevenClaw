"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { SolutionWizardLayout } from "@/components/solutions/wizard/solution-wizard-layout";
import { StepModernizeDiagnose } from "@/components/solutions/wizard/steps/step-modernize-diagnose";
import { StepModernizeDiagnosisReview } from "@/components/solutions/wizard/steps/step-modernize-diagnosis-review";
import { StepModernizeRepoConnect } from "@/components/solutions/wizard/steps/step-modernize-repo-connect";
import { StepModernizeRepoSelect } from "@/components/solutions/wizard/steps/step-modernize-repo-select";
import { isModernizeEnabled } from "@/lib/feature-flags";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

/**
 * Modernize 위저드 entry page — `/solutions/modernize/new`.
 *
 * M6 범위: Step 0~3 (repo-connect → repo-select → diagnose → diagnosis-review) 구현.
 * 이후 step (공유 PM/agents/...) 는 M7 에서 추가.
 *
 * `isModernizeEnabled()` flag OFF 시 즉시 dashboard 로 redirect — 베타 사용자만 노출.
 */

// 인덱스: 0=repo-connect, 1=repo-select, 2=diagnose, 3=diagnosis-review
const STEP_COMPONENTS = [
  StepModernizeRepoConnect,
  StepModernizeRepoSelect,
  StepModernizeDiagnose,
  StepModernizeDiagnosisReview,
];

export default function ModernizeNewPage() {
  const router = useRouter();
  const setMode = useSolutionWizardStore((s) => s.setMode);
  const currentStep = useSolutionWizardStore((s) => s.currentStep);
  const nextStep = useSolutionWizardStore((s) => s.nextStep);
  const installationPk = useSolutionWizardStore(
    (s) => s.modernize.githubInstallationPk,
  );
  const repo = useSolutionWizardStore((s) => s.modernize.repo);
  const diagnoseDone = useSolutionWizardStore((s) => s.modernize.diagnoseDone);
  const scenario = useSolutionWizardStore((s) => s.modernize.scenario);
  const acceptedIds = useSolutionWizardStore(
    (s) => s.modernize.acceptedRecommendationIds,
  );

  // Feature flag OFF 시 즉시 redirect
  useEffect(() => {
    if (!isModernizeEnabled()) {
      router.replace("/projects");
      return;
    }
    setMode("modernize");
  }, [router, setMode]);

  const safeStep = Math.min(currentStep, STEP_COMPONENTS.length - 1);
  const StepComponent = STEP_COMPONENTS[safeStep];

  // 각 step canProceed
  const canProceed = (() => {
    switch (safeStep) {
      case 0:
        return installationPk !== null;
      case 1:
        return !!repo?.fullName && !!repo?.branch;
      case 2:
        return diagnoseDone;
      case 3:
        return scenario !== null && acceptedIds.length > 0;
      default:
        return false;
    }
  })();

  const isLastStep = safeStep === STEP_COMPONENTS.length - 1;

  return (
    <SolutionWizardLayout
      currentStep={safeStep}
      canProceed={canProceed}
      mode="modernize"
      onSubmit={
        isLastStep
          ? () => {
              // M7 에서 PM/agents/env/confirm 공유 step 재사용 + Linear 자동 등록 + ZIP 생성 연결 예정.
              alert(
                "M7 (공유 step + Linear 등록 + ZIP 생성) 구현 후 다음 단계로 자동 진입합니다.",
              );
            }
          : undefined
      }
      onNextStep={async () => {
        // Step 1 (repo-select) → Step 2 (diagnose) 로 진행 시 diagnose 의 useEffect 가
        // 자동으로 POST /sessions 호출. 별도 트리거 X.
        nextStep();
      }}
    >
      <StepComponent />
    </SolutionWizardLayout>
  );
}
