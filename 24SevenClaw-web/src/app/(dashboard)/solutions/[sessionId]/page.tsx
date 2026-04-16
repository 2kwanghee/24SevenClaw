"use client";

import { useRouter, useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";

import { SolutionWizardLayout } from "@/components/solutions/wizard/solution-wizard-layout";
import {
  StepCompany,
  StepPrototypeGeneration,
  StepPrototypes,
  StepPMSelect,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionEnv,
  StepConfirmation,
} from "@/components/solutions/wizard/steps";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { prototypeSessions, ApiClientError } from "@/lib/api-client";

// 인덱스: 0=회사정보, 1=솔루션생성(로딩), 2=프로토타입선택, 3=PM, 4=에이전트, 5=플랫폼, 6=환경변수, 7=최종확인
const STEP_COMPONENTS = [
  StepCompany,
  StepPrototypeGeneration,
  StepPrototypes,
  StepPMSelect,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionEnv,
  StepConfirmation,
];

export default function SolutionSessionPage() {
  const router = useRouter();
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;

  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const {
    currentStep,
    data,
    setSessionId,
    setOrganizationId,
    setCompany,
    setGeneratedPrototypes,
    goToStep,
  } = useSolutionWizardStore();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const restoredRef = useRef(false);

  // 기존 세션 복원
  useEffect(() => {
    if (!token || !sessionId) return;
    // 이미 복원했으면 재실행 방지
    if (restoredRef.current) {
      setIsLoading(false);
      return;
    }

    const restore = async () => {
      setIsLoading(true);
      try {
        const ps = await prototypeSessions.get(token, sessionId);
        setSessionId(ps.id);
        setOrganizationId(ps.organization_id);

        // solution_prompt에서 솔루션 요청 복원 (개별 필드는 복원 불가)
        setCompany({
          companyName: "",
          mainProduct: "",
          businessType: null,
          companyDescription: "",
          solutionRequest: ps.solution_prompt ?? "",
        });

        // 세션 상태에 따라 적절한 스텝으로 이동 (step 0에 있으면)
        if (currentStep === 0) {
          if (ps.status === "completed") {
            // 완료된 세션: 프로토타입 목록 복원 후 선택 단계로 이동
            try {
              const protoList = await prototypeSessions.listPrototypes(
                token,
                ps.id,
              );
              if (protoList.items.length > 0) {
                setGeneratedPrototypes(
                  protoList.items.map((p) => ({
                    id: p.id,
                    name: p.title,
                    solutionType: p.design_pattern ?? "custom",
                    reasoning: p.description,
                    config: (p.ui_structure ?? {}) as Record<string, unknown>,
                  })),
                );
                goToStep(2); // 프로토타입 선택 단계로 바로 이동
              } else {
                goToStep(1); // 프로토타입 없으면 생성 단계부터
              }
            } catch {
              goToStep(1); // 실패 시 생성 단계부터
            }
          } else {
            // generating/pending: 생성 단계로 이동
            goToStep(1);
          }
        }

        restoredRef.current = true;
      } catch {
        // 세션 없으면 새 세션 생성 페이지로
        router.replace("/solutions/new");
      } finally {
        setIsLoading(false);
      }
    };

    void restore();
  }, [
    token,
    sessionId,
    currentStep,
    setSessionId,
    setOrganizationId,
    setCompany,
    setGeneratedPrototypes,
    goToStep,
    router,
  ]);

  const StepComponent = STEP_COMPONENTS[currentStep];

  // 인덱스: 0=회사정보, 1=솔루션생성(자동이동), 2=프로토타입선택, 3=PM, 4=에이전트, 5=플랫폼, 6=환경변수, 7=최종확인
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
        // 솔루션 생성 단계: 자동 이동, 수동 진행 불가
        return false;
      case 2:
        return !!data.prototypes.selectedPrototypeId;
      case 4:
        return data.agents.selectedAgents.length > 0;
      case 5:
        return !!data.platform.platformId;
      default:
        return true;
    }
  })();

  const handleSubmit = async () => {
    if (!token) return;
    if (!data.sessionId) {
      setError("세션 정보가 없습니다. 처음부터 다시 시작해 주세요.");
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

      router.push(`/projects/${result.project_id}`);
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

  if (isLoading) {
    return (
      <div
        className="flex h-64 items-center justify-center"
        role="status"
        aria-label="세션 불러오는 중"
      >
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
        <span className="sr-only">세션을 복원하고 있습니다...</span>
      </div>
    );
  }

  return (
    <SolutionWizardLayout
      onSubmit={handleSubmit}
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
              void handleSubmit();
            }}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-300 transition-colors hover:bg-red-500/10"
          >
            <RefreshCw className="h-3 w-3" aria-hidden="true" />
            재시도
          </button>
        </div>
      )}

      <StepComponent />
    </SolutionWizardLayout>
  );
}
