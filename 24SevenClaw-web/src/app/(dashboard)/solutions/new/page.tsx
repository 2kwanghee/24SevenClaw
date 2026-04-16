"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { SolutionWizardLayout } from "@/components/solutions/wizard/solution-wizard-layout";
import {
  StepCompany,
  StepPrototypes,
  StepPMSelect,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionEnv,
  StepSolutionConfirm,
} from "@/components/solutions/wizard/steps";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { apiClient, organizations, prototypeSessions, ApiClientError } from "@/lib/api-client";

const STEP_COMPONENTS = [
  StepCompany,
  StepPrototypes,
  StepPMSelect,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionEnv,
  StepSolutionConfirm,
];

export default function NewSolutionPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const {
    currentStep,
    data,
    nextStep,
    setSessionId,
    setOrganizationId,
    reset,
  } = useSolutionWizardStore();

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 페이지 진입 시 위저드 초기화
  useEffect(() => {
    reset();
  }, [reset]);

  const StepComponent = STEP_COMPONENTS[currentStep];

  // 각 스텝별 진행 가능 여부
  const canProceed = (() => {
    switch (currentStep) {
      case 0:
        return !!(
          data.company.companyName &&
          data.company.mainProduct &&
          data.company.businessType &&
          data.company.solutionRequest.length >= 10
        );
      case 1:
        return !!data.prototypes.selectedPrototypeId;
      case 3:
        return data.agents.selectedAgents.length > 0;
      case 4:
        return !!data.platform.platformId;
      default:
        return true;
    }
  })();

  /** Step 1 완료 시: 조직 upsert → 프로토타입 세션 생성 → Step 2로 이동 */
  const handleStep1Next = async () => {
    if (!token) return;
    setError(null);
    setIsSubmitting(true);
    try {
      // 1. 조직 정보 저장/업데이트
      const org = await organizations.upsert(token, {
        company_name: data.company.companyName,
        main_product: data.company.mainProduct,
        // b2b2c는 API 미지원으로 b2b로 매핑
        business_type:
          data.company.businessType === "b2b2c"
            ? "b2b"
            : (data.company.businessType ?? undefined),
        company_description: data.company.companyDescription || undefined,
      });
      setOrganizationId(org.id);

      // 2. 프로토타입 세션 생성
      const ps = await prototypeSessions.create(token, {
        organization_id: org.id,
        user_input: {
          company_name: data.company.companyName,
          main_product: data.company.mainProduct,
          business_type: data.company.businessType,
          company_description: data.company.companyDescription,
          solution_request: data.company.solutionRequest,
        },
      });
      setSessionId(ps.id);

      // 3. Step 2로 이동 (URL 업데이트 + 세션 ID 반영)
      nextStep();
      router.replace(`/solutions/${ps.id}`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("세션 생성에 실패했습니다.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  /** 마지막 스텝: 프로젝트 생성 */
  const handleSubmit = async () => {
    if (!token || !data.company.companyName) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const project = await apiClient.projects.create(token, {
        name: data.company.companyName,
        description: data.company.solutionRequest || undefined,
      });

      reset();
      router.push(`/projects/${project.id}/dashboard`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("프로젝트 생성에 실패했습니다.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SolutionWizardLayout
      onSubmit={handleSubmit}
      onNextStep={handleStep1Next}
      isSubmitting={isSubmitting}
      canProceed={canProceed}
    >
      {error && (
        <div
          role="alert"
          className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400" aria-hidden="true" />
          <p className="flex-1 text-sm text-red-300">{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              void handleStep1Next();
            }}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-300 transition-colors hover:bg-red-500/10"
          >
            <RefreshCw className="h-3 w-3" />
            재시도
          </button>
        </div>
      )}

      <StepComponent />
    </SolutionWizardLayout>
  );
}
