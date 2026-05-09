"use client";

import { useRouter, useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { AlertCircle, RefreshCw } from "lucide-react";

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
  StepSolutionOS,
  StepSolutionEnv,
  StepSolutionRoi,
  StepConfirmation,
} from "@/components/solutions/wizard/steps";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { prototypeSessions, integrations, anthropicCredentials } from "@/lib/api-client";
import { useCatalogSkills } from "@/hooks/use-catalog";
import { toast } from "sonner";

// 인덱스: 0=회사정보, 1=솔루션생성, 2=프로토타입선택, 3=PM추천, 4=PM선택, 5=PM구성, 6=에이전트, 7=플랫폼, 8=OS환경, 9=환경변수, 10=ROI비교, 11=최종확인
const STEP_COMPONENTS = [
  StepCompanySolution,
  StepPrototypeGeneration,
  StepPrototypeSelection,
  StepPMRecommendation,
  StepPMSelection,
  StepPMComposition,
  StepSolutionAgents,
  StepSolutionPlatform,
  StepSolutionOS,
  StepSolutionEnv,
  StepSolutionRoi,
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
    step1Done,
    step3Done,
    envValidation,
    setSessionId,
    setOrganizationId,
    setCompany,
    setGeneratedPrototypes,
    setCreatedProjectId,
    goToStep,
  } = useSolutionWizardStore();

  const { data: skillsData, isLoading: skillsLoading } = useCatalogSkills();

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const restoredRef = useRef(false);

  // 기존 세션 복원
  useEffect(() => {
    if (!token || !sessionId) return;
    if (restoredRef.current) return;

    const restore = async () => {
      try {
        const ps = await prototypeSessions.get(token, sessionId);
        setSessionId(ps.id);
        setOrganizationId(ps.organization_id);

        // API는 company 상세 정보를 반환하지 않으므로 solutionRequest만 병합
        // companyName / mainProduct / businessType 등은 step 1에서 입력한 store 값을 유지
        setCompany({
          solutionRequest: ps.solution_prompt ?? "",
        });

        if (currentStep === 0) {
          if (ps.status === "completed") {
            try {
              const protoList = await prototypeSessions.getPrototypes(
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
                    techStack: Array.isArray(p.tech_stack_tags) ? p.tech_stack_tags : [],
                    architecturePattern: p.architecture_pattern ?? undefined,
                    rationale: p.variant_rationale ?? undefined,
                    isRecommended: p.is_recommended,
                    pros: Array.isArray(p.pros) ? p.pros : [],
                    cons: Array.isArray(p.cons) ? p.cons : [],
                  })),
                );
                goToStep(2);
              } else {
                goToStep(1);
              }
            } catch {
              goToStep(1);
            }
          } else {
            goToStep(1);
          }
        }

        restoredRef.current = true;
      } catch {
        router.replace("/solutions/new");
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

  // 인덱스: 0=회사정보, 1=솔루션생성(자동), 2=프로토타입선택, 3=PM추천(자동), 4=PM선택, 5=PM구성, 6=에이전트, 7=플랫폼, 8=OS환경, 9=환경변수, 10=ROI비교, 11=최종확인
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
        return step1Done;
      case 2:
        return !!data.prototypes.selectedPrototypeId;
      case 3:
        return step3Done;
      case 4:
        return !!data.pm.selectedPmProfileId;
      case 5:
        return true;
      case 6: {
        if (data.agents.selectedAgents.length === 0) return false;
        if (skillsLoading || !skillsData) return false;
        const ticketSourceIds = skillsData.items
          .filter((s) => s.category === "ticket_source")
          .map((s) => s.id);
        if (
          ticketSourceIds.length > 0 &&
          !data.agents.selectedSkills.some((s) => ticketSourceIds.includes(s))
        ) {
          return false;
        }
        return true;
      }
      case 7:
        return !!data.platform.platformId;
      case 8:
        return !!data.os.osId;
      case 9: {
        const ev = data.env.envVars;
        const am = data.env.authMethod ?? "api_key";
        if (am === "api_key" && !ev["ANTHROPIC_API_KEY"]?.trim()) return false;
        if (am === "oauth_setup_token" && !data.env.oauthSetupToken?.trim()) return false;
        // 선택된 스킬의 required env_vars 전체 검증
        if (skillsData?.items) {
          for (const skill of skillsData.items) {
            if (!data.agents.selectedSkills.includes(skill.id)) continue;
            for (const v of skill.env_vars) {
              if (v.required && !ev[v.name]?.trim()) return false;
            }
          }
        }
        // 라이브 검증 (linear / notion)
        if (data.agents.selectedSkills.includes("linear")) {
          if (envValidation.linearStatus !== "valid") return false;
        }
        if (data.agents.selectedSkills.includes("notion")) {
          if (envValidation.notionStatus !== "valid") return false;
        }
        return true;
      }
      case 10:
        return !!data.roi.result;
      default:
        return true;
    }
  })();

  // Next.js 프록시 라우트를 통해 finalize 호출
  // 브라우저 → /api/solutions/{id}/finalize (같은 출처) → FastAPI (서버사이드)
  const handleSubmit = async () => {
    const effectiveSessionId = data.sessionId ?? sessionId;
    if (!effectiveSessionId) {
      setError("세션 정보가 없습니다. 처음부터 다시 시작해 주세요.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      // oauth_setup_token 먼저 저장 — finalize 전에 실행해야 재다운로드 시 CLAUDE_CODE_OAUTH_TOKEN 주입 가능
      if (
        data.env.authMethod === "oauth_setup_token" &&
        data.env.oauthSetupToken?.trim()
      ) {
        try {
          await anthropicCredentials.saveSetupToken(
            token,
            data.env.oauthSetupToken.trim(),
          );
        } catch {
          const msg = "OAuth Setup Token 저장에 실패했습니다. 다시 시도해 주세요.";
          toast.error(msg);
          setError(msg);
          return;
        }
      }

      const res = await fetch(`/api/solutions/${effectiveSessionId}/finalize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name:
            data.company.companyName ||
            `솔루션 프로젝트 ${new Date().toLocaleDateString("ko-KR")}`,
          description: data.company.solutionRequest || null,
          // ZIP 재다운로드를 위해 wizard 설정 저장
          wizard_data: {
            organization: {
              companyName: data.company.companyName,
              mainProduct: data.company.mainProduct,
              businessType: data.company.businessType,
              companyDescription: data.company.companyDescription,
            },
            solution: {
              solutionRequest: data.company.solutionRequest,
              enableAutoDecompose: data.company.enableAutoDecompose,
              authMethod: data.env.authMethod ?? "api_key",
            },
            agents: data.agents.selectedAgents.map((id) => ({ id })),
            skills: data.agents.selectedSkills.map((id) => ({ id })),
            hooks: (data.agents.selectedHooks ?? []).map((id) => ({ id })),
            pipelines: [],
            platform: { platformId: data.platform.platformId ?? null },
          },
        }),
      });

      if (res.status === 401) {
        const msg = "세션이 만료되었습니다. 다시 로그인해 주세요.";
        toast.error(msg);
        setError(msg);
        return;
      }

      const body = (await res.json().catch(() => ({}))) as {
        project_id?: string;
        detail?: string;
      };

      if (!res.ok) {
        const msg =
          typeof body.detail === "string"
            ? body.detail
            : "프로젝트 생성에 실패했습니다.";
        toast.error(msg);
        setError(msg);
        return;
      }

      if (body.project_id) {
        setCreatedProjectId(body.project_id);
        const ev = useSolutionWizardStore.getState().data.env.envVars;
        const hasLinear = !!ev["LINEAR_API_KEY"] && !!ev["LINEAR_TEAM_ID"];
        const hasNotion = !!ev["NOTION_API_KEY"] && !!ev["NOTION_DATABASE_ID"];
        if (hasLinear || hasNotion) {
          void integrations
            .registerInitialTasks(token, body.project_id, {
              linear_api_key: hasLinear ? ev["LINEAR_API_KEY"] : null,
              linear_team_id: hasLinear ? ev["LINEAR_TEAM_ID"] : null,
              notion_api_key: hasNotion ? ev["NOTION_API_KEY"] : null,
              notion_database_id: hasNotion ? ev["NOTION_DATABASE_ID"] : null,
              project_name:
                data.company.companyName ||
                `솔루션 프로젝트 ${new Date().toLocaleDateString("ko-KR")}`,
            })
            .catch(() => {});
        }
      }
    } catch {
      const msg = "네트워크 연결을 확인해 주세요";
      toast.error(msg);
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SolutionWizardLayout
      onSubmit={handleSubmit}
      isSubmitting={isSubmitting}
      canProceed={canProceed}
      nextLabel={currentStep === 5 ? "이대로 진행" : undefined}
    >
      {error && (
        <div
          role="alert"
          className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-red-700" aria-hidden="true" />
          <p className="flex-1 text-sm text-red-700">{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              void handleSubmit();
            }}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-700 transition-colors hover:bg-red-100"
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
