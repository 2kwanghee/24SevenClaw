"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { SolutionWizardLayout } from "@/components/solutions/wizard/solution-wizard-layout";
import { StepModernizeDiagnose } from "@/components/solutions/wizard/steps/step-modernize-diagnose";
import { StepModernizeRepoConnect } from "@/components/solutions/wizard/steps/step-modernize-repo-connect";
import { StepModernizeRepoSelect } from "@/components/solutions/wizard/steps/step-modernize-repo-select";
import { isModernizeEnabled } from "@/lib/feature-flags";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

/**
 * Modernize 위저드 entry page — `/solutions/modernize/new`.
 *
 * M5 범위: Step 0~2 (repo-connect → repo-select → diagnose) 구현.
 * 이후 step (diagnosis-review / 공유 PM/agents/...) 는 M6~M7 에서 추가.
 *
 * `isModernizeEnabled()` flag OFF 시 즉시 dashboard 로 redirect — 베타 사용자만 노출.
 */

// 인덱스: 0=repo-connect, 1=repo-select, 2=diagnose
const STEP_COMPONENTS = [
  StepModernizeRepoConnect,
  StepModernizeRepoSelect,
  StepModernizeDiagnose,
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
              // M6 에서 diagnosis-review step 추가 + 권장안 검토 흐름 연결 예정.
              alert(
                "M6 (권장안 생성 + 검토 UI) 구현 후 다음 단계로 자동 진입합니다.",
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
