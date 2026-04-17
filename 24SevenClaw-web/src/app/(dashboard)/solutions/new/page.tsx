"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { SolutionWizardLayout } from "@/components/solutions/wizard/solution-wizard-layout";
import {
  StepCompanySolution,
  StepPrototypeGeneration,
  StepPrototypeSelection,
  StepPMRecommendation,
  StepPMSelection,
  StepPMComposition,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionEnv,
  StepConfirmation,
} from "@/components/solutions/wizard/steps";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { organizations, prototypeSessions, ApiClientError, NetworkError } from "@/lib/api-client";

// 인덱스: 0=회사정보, 1=솔루션생성(로딩), 2=프로토타입선택, 3=PM추천(자동), 4=PM선택, 5=PM구성확인, 6=에이전트, 7=플랫폼, 8=환경변수, 9=최종확인
const STEP_COMPONENTS = [
  StepCompanySolution,
  StepPrototypeGeneration,
  StepPrototypeSelection,
  StepPMRecommendation,
  StepPMSelection,
  StepPMComposition,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionEnv,
  StepConfirmation,
];

export default function NewSolutionPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const {
    currentStep,
    data,
    step0Valid,
    step1Done,
    step3Done,
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
  // 인덱스: 0=회사정보, 1=솔루션생성(자동), 2=프로토타입선택, 3=PM추천(자동), 4=PM선택, 5=PM구성확인, 6=에이전트, 7=플랫폼, 8=환경변수, 9=최종확인
  const canProceed = (() => {
    switch (currentStep) {
      case 0:
        // formState.isValid를 스토어에 동기화한 값으로 판단 (store 간접 참조 사이클 회피)
        return step0Valid;
      case 1:
        return step1Done;
      case 2:
        return !!data.prototypes.selectedPrototypeId;
      case 3:
        return step3Done;
      case 4:
        return !!data.pm.selectedPmProfileId;
      case 5:
        // PM 구성 확인 단계: 항상 진행 가능 (검토 후 이대로 진행)
        return true;
      case 6:
        return data.agents.selectedAgents.length > 0;
      case 7:
        return !!data.platform.platformId;
      default:
        return true;
    }
  })();

  /** Step 1 완료 시: 조직 upsert → 프로토타입 세션 생성 → Step 2로 이동 */
  const handleStep1Next = async () => {
    if (!token) {
      toast.error("로그인이 필요합니다. 페이지를 새로고침해 주세요.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      // 클릭 시점의 최신 스토어 값 사용 (렌더 클로저 stale 방지)
      const company = useSolutionWizardStore.getState().data.company;

      // 1. 조직 정보 저장/업데이트
      const org = await organizations.upsert(token, {
        company_name: company.companyName,
        main_product: company.mainProduct,
        // b2b2c는 API 미지원으로 b2b로 매핑
        business_type:
          company.businessType === "b2b2c"
            ? "b2b"
            : (company.businessType ?? undefined),
        company_description: company.companyDescription || undefined,
      });
      setOrganizationId(org.id);

      // 2. 프로토타입 세션 생성
      const ps = await prototypeSessions.create(token, {
        organization_id: org.id,
        solution_prompt: company.solutionRequest,
        tech_stack: company.techStack,
      });
      setSessionId(ps.id);

      // 3. Step 2로 이동 (URL 업데이트 + 세션 ID 반영)
      nextStep();
      router.replace(`/solutions/${ps.id}`);
    } catch (err) {
      if (err instanceof NetworkError) {
        toast.error(err.message);
        setError(err.message);
      } else if (err instanceof ApiClientError) {
        toast.error(err.detail);
        setError(err.detail);
      } else {
        const msg = "세션 생성에 실패했습니다.";
        toast.error(msg);
        setError(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  /** 마지막 스텝: prototype-session finalize → 프로젝트 생성 */
  const handleSubmit = async () => {
    if (!token) {
      toast.error("로그인이 필요합니다. 페이지를 새로고침해 주세요.");
      return;
    }
    if (!data.sessionId) {
      const msg = "세션 정보가 없습니다. 처음부터 다시 시작해 주세요.";
      toast.error(msg);
      setError(msg);
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await prototypeSessions.finalize(token, data.sessionId, {
        project_name:
          data.company.companyName ||
          `솔루션 프로젝트 ${new Date().toLocaleDateString("ko-KR")}`,
        description: data.company.solutionRequest || null,
      });

      reset();
      router.push(`/projects/${result.project_id}`);
    } catch (err) {
      if (err instanceof NetworkError) {
        toast.error(err.message);
        setError(err.message);
      } else if (err instanceof ApiClientError) {
        toast.error(err.detail);
        setError(err.detail);
      } else {
        const msg = "프로젝트 생성에 실패했습니다.";
        toast.error(msg);
        setError(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SolutionWizardLayout
      onSubmit={handleSubmit}
      onNextStep={currentStep === 0 ? handleStep1Next : undefined}
      isSubmitting={isSubmitting}
      canProceed={canProceed}
      nextLabel={currentStep === 5 ? "이대로 진행" : undefined}
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
