"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { SolutionWizardLayout } from "@/components/solutions/wizard/solution-wizard-layout";
import { StepModernizeRepoConnect } from "@/components/solutions/wizard/steps/step-modernize-repo-connect";
import { StepModernizeRepoSelect } from "@/components/solutions/wizard/steps/step-modernize-repo-select";
import { isModernizeEnabled } from "@/lib/feature-flags";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

/**
 * Modernize 위저드 entry page — `/solutions/modernize/new`.
 *
 * M4 범위: Step 0 (repo-connect) + Step 1 (repo-select) 만 구현. 이후 step
 * (diagnose / diagnosis-review / 공유 PM/agents/...)는 M5~M7 에서 추가.
 *
 * `isModernizeEnabled()` flag OFF 시 즉시 dashboard 로 redirect — 베타 사용자만 노출.
 */

// MVP-2-A M4 시점의 step 목록. M5~M7 에서 확장됨.
// 인덱스: 0=repo-connect, 1=repo-select
const STEP_COMPONENTS = [StepModernizeRepoConnect, StepModernizeRepoSelect];

export default function ModernizeNewPage() {
  const router = useRouter();
  const setMode = useSolutionWizardStore((s) => s.setMode);
  const currentStep = useSolutionWizardStore((s) => s.currentStep);
  const installationPk = useSolutionWizardStore(
    (s) => s.modernize.githubInstallationPk,
  );
  const repo = useSolutionWizardStore((s) => s.modernize.repo);

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
              // M5 에서 ModernizeSession 생성 + diagnose step 으로 진행 예정.
              // 현재는 placeholder.
              alert(
                "M5 (코드 분석 엔진) 구현 후 진단 단계로 자동 진입합니다.",
              );
            }
          : undefined
      }
    >
      <StepComponent />
    </SolutionWizardLayout>
  );
}
