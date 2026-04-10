"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { AlertCircle, RefreshCw } from "lucide-react";

import { WizardLayout } from "@/components/projects/wizard/wizard-layout";
import {
  StepOrganization,
  StepSolution,
  StepAgents,
  StepSkills,
  StepPipelines,
  StepPlatform,
  StepPreview,
} from "@/components/projects/wizard/steps";
import { useWizardStore } from "@/stores/wizard-store";
import { useCreateProject } from "@/hooks/use-projects";
import { apiClient, ApiClientError } from "@/lib/api-client";

const STEP_COMPONENTS = [
  StepOrganization,
  StepSolution,
  StepAgents,
  StepSkills,
  StepPipelines,
  StepPlatform,
  StepPreview,
];

export default function NewProjectPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const createProject = useCreateProject();
  const { currentStep, data, reset } = useWizardStore();
  const [error, setError] = useState<string | null>(null);

  // 페이지 진입 시 위저드 초기화
  useEffect(() => {
    reset();
  }, [reset]);

  const StepComponent = STEP_COMPONENTS[currentStep];

  // 각 스텝별 필수 필드 입력 여부 판단
  const canProceed = (() => {
    switch (currentStep) {
      case 0:
        return !!(
          data.organization.companyName &&
          data.organization.companySize &&
          data.organization.industry
        );
      case 1:
        return !!(data.solution.projectName && data.solution.solutionType);
      case 2:
        return data.agents.selectedAgents.length > 0;
      default:
        return true;
    }
  })();

  const handleSubmit = () => {
    if (!data.organization.companyName) return;

    setError(null);
    createProject.mutate(
      {
        name: data.solution.projectName || data.organization.companyName,
        description: data.solution.description || undefined,
      },
      {
        onSuccess: async (project) => {
          // 프로젝트 생성 후 위저드 설정 저장
          try {
            await apiClient.projects.saveConfig(token, project.id, {
              organization: data.organization as unknown as Record<string, unknown>,
              solution: data.solution as unknown as Record<string, unknown>,
              agents: data.agents.selectedAgents.map((id) => ({ id })),
              skills: data.skills.selectedSkills.map((s) => ({ id: s.id })),
              pipelines: data.pipelines.selectedPipelines.map((id) => ({ id })),
              platform: data.platform as unknown as Record<string, unknown>,
            });
          } catch {
            // config 저장 실패해도 프로젝트 생성은 성공했으므로 계속 진행
          }
          reset();
          router.push("/projects");
        },
        onError: (err) => {
          if (err instanceof ApiClientError) {
            setError(err.detail);
          } else {
            setError("프로젝트 생성에 실패했습니다.");
          }
        },
      },
    );
  };

  return (
    <WizardLayout
      onSubmit={handleSubmit}
      isSubmitting={createProject.isPending}
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
              handleSubmit();
            }}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-300 transition-colors hover:bg-red-500/10"
          >
            <RefreshCw className="h-3 w-3" />
            재시도
          </button>
        </div>
      )}

      <StepComponent />
    </WizardLayout>
  );
}
