"use client";

import { useRouter, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";

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
import {
  apiClient,
  prototypeSessions,
  ApiClientError,
} from "@/lib/api-client";

const STEP_COMPONENTS = [
  StepCompany,
  StepPrototypes,
  StepPMSelect,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionEnv,
  StepSolutionConfirm,
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
    reset,
  } = useSolutionWizardStore();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 기존 세션 복원
  useEffect(() => {
    if (!token || !sessionId) return;

    const restore = async () => {
      setIsLoading(true);
      try {
        const ps = await prototypeSessions.get(token, sessionId);
        setSessionId(ps.id);
        setOrganizationId(ps.organization_id);
      } catch {
        // 세션 없으면 새 세션 생성 페이지로
        router.replace("/solutions/new");
      } finally {
        setIsLoading(false);
      }
    };

    void restore();
  }, [token, sessionId, setSessionId, setOrganizationId, router]);

  const StepComponent = STEP_COMPONENTS[currentStep];

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

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
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
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
          <p className="flex-1 text-sm text-red-300">{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              void handleSubmit();
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
