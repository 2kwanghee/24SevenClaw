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
import { prototypeSessions, integrations, organizations } from "@/lib/api-client";
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

        // organizations.me()로 조직 정보 복원 — 새 탭/새로고침 시 store 유실 방어
        try {
          const org = await organizations.me(token);
          setCompany({
            companyName: org.company_name,
            mainProduct: org.main_product ?? "",
            businessType: (org.business_type ?? null) as "b2b" | "b2c" | "b2b2c" | null,
            companyDescription: org.company_description ?? "",
            solutionRequest: ps.solution_prompt ?? "",
          });
        } catch {
          setCompany({ solutionRequest: ps.solution_prompt ?? "" });
        }

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
                    // 정량 지표 (Phase A)
                    estimatedWeeksMin: p.estimated_weeks_min ?? null,
                    estimatedWeeksMax: p.estimated_weeks_max ?? null,
                    teamSizeMin: p.team_size_min ?? null,
                    teamSizeMax: p.team_size_max ?? null,
                    teamRoles: p.team_roles ?? [],
                    complexityScore: p.complexity_score ?? null,
                    scalabilityScore: p.scalability_score ?? null,
                    monthlyCostMinUsd: p.monthly_cost_min_usd ?? null,
                    monthlyCostMaxUsd: p.monthly_cost_max_usd ?? null,
                    maintenanceDifficulty: p.maintenance_difficulty ?? null,
                    skillRequirements: p.skill_requirements ?? [],
                    matchReasoning: p.match_reasoning ?? null,
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
        if (ticketSourceIds.length > 0) {
          // PM 이 ticket_source 통합을 MCP 서버로만 잠금한 케이스도 인정 (new/page.tsx 와 동일 정책)
          const selectedMcps = data.agents.selectedMcps ?? [];
          const hasTicketSource =
            data.agents.selectedSkills.some((s) => ticketSourceIds.includes(s)) ||
            selectedMcps.some((m) => ticketSourceIds.includes(m));
          if (!hasTicketSource) return false;
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
        const deferred = data.env.deferredEnvVars ?? [];
        // Anthropic 자격증명만 진짜 필수 (deferred로 우회 가능)
        if (am === "api_key" && !ev["ANTHROPIC_API_KEY"]?.trim() && !deferred.includes("ANTHROPIC_API_KEY")) return false;
        // 외부 통합 스킬(linear/notion 등) required env_vars 는 미입력이어도 통과 — new/page.tsx와 동일 정책.
        // 라이브 검증: invalid 일 때만 차단. idle/loading 은 통과.
        if (data.agents.selectedSkills.includes("linear") && envValidation.linearStatus === "invalid") {
          return false;
        }
        if (data.agents.selectedSkills.includes("notion") && envValidation.notionStatus === "invalid") {
          return false;
        }
        return true;
      }
      case 10:
        return !!data.roi.result;
      case 11: {
        // 최종 확인 — deferred 입력란에서 라이브 검증이 invalid 이면 ZIP 다운로드 차단.
        // step 9 와 동일 정책: idle/loading/valid 통과.
        if (data.agents.selectedSkills.includes("linear") && envValidation.linearStatus === "invalid") {
          return false;
        }
        if (data.agents.selectedSkills.includes("notion") && envValidation.notionStatus === "invalid") {
          return false;
        }
        return true;
      }
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
    if (!data.company.companyName?.trim()) {
      const msg = "회사 이름이 없습니다. 1단계로 돌아가 회사 이름을 입력해 주세요.";
      toast.error(msg);
      setError(msg);
      goToStep(0);
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {

      const res = await fetch(`/api/solutions/${effectiveSessionId}/finalize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: data.company.companyName,
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
            mcps: (data.agents.selectedMcps ?? []).map((id) => ({ id })),
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
              project_name: data.company.companyName,
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
