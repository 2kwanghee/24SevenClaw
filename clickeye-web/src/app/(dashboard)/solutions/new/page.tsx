"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { AlertCircle, ArrowRight, RefreshCw, Trash2 } from "lucide-react";
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
  StepSolutionOS,
  StepSolutionEnv,
  StepSolutionRoi,
  StepConfirmation,
} from "@/components/solutions/wizard/steps";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { organizations, prototypeSessions, integrations, ApiClientError, NetworkError, type PrototypeSessionResponse } from "@/lib/api-client";
import { useCatalogSkills } from "@/hooks/use-catalog";
import { BaseModal } from "@/components/common/base-modal";
import { cn } from "@/lib/utils";

// 인덱스: 0=회사정보, 1=솔루션생성(로딩), 2=프로토타입선택, 3=PM추천(자동), 4=PM선택, 5=PM구성확인, 6=에이전트, 7=플랫폼, 8=OS환경, 9=환경변수, 10=ROI비교, 11=최종확인
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
    envValidation,
    nextStep,
    goToStep,
    setSessionId,
    setOrganizationId,
    setCreatedProjectId,
    reset,
  } = useSolutionWizardStore();

  const { data: skillsData, isLoading: skillsLoading } = useCatalogSkills();

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pendingSessions, setPendingSessions] = useState<PrototypeSessionResponse[]>([]);
  const [showResumeDialog, setShowResumeDialog] = useState(false);
  const resumeCheckedRef = useRef(false);

  // 페이지 진입 시 위저드 초기화
  useEffect(() => {
    reset();
  }, [reset]);

  // 토큰 확보 후 한 번만 미완료 세션 확인
  useEffect(() => {
    if (!token || resumeCheckedRef.current) return;
    resumeCheckedRef.current = true;

    void prototypeSessions
      .list(token, { limit: 10 })
      .then((sessions) => {
        const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
        const recent = sessions.filter(
          (s) =>
            s.status !== "failed" &&
            new Date(s.created_at).getTime() > sevenDaysAgo,
        );
        if (recent.length > 0) {
          setPendingSessions(recent);
          setShowResumeDialog(true);
        }
      })
      .catch(() => {});
  }, [token]);

  const StepComponent = STEP_COMPONENTS[currentStep];

  // 각 스텝별 진행 가능 여부
  // 인덱스: 0=회사정보, 1=솔루션생성(자동), 2=프로토타입선택, 3=PM추천(자동), 4=PM선택, 5=PM구성확인, 6=에이전트, 7=플랫폼, 8=OS환경, 9=환경변수, 10=ROI비교, 11=최종확인
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
      case 6: {
        if (data.agents.selectedAgents.length === 0) return false;
        // 카탈로그 로딩 중에는 티켓 소스 검증 불가 → 차단
        if (skillsLoading || !skillsData) return false;
        const ticketSourceIds = skillsData.items
          .filter((s) => s.category === "ticket_source")
          .map((s) => s.id);
        if (ticketSourceIds.length > 0) {
          // PM 이 ticket_source 통합(linear/notion 등)을 MCP 서버로만 잠금한 케이스가 있어
          // selectedSkills 와 selectedMcps 양쪽에서 충족 여부를 확인한다.
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
        // 외부 통합 스킬(linear/notion 등) required env_vars 는 미입력이어도 통과.
        // UI 경고 + 나중에 입력 + ZIP의 docs/api-keys 가이드로 처리한다.
        // 라이브 검증: 사용자가 잘못된 키를 입력한 경우(invalid)만 차단. idle/loading 은 통과.
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

      // 2. 프로토타입 세션 생성 — 회사 컨텍스트 전부 전달
      const ps = await prototypeSessions.create(token, {
        organization_id: org.id,
        solution_prompt: company.solutionRequest,
        tech_stack: company.techStack,
        industry: company.industry ?? null,
        company_size: company.companySize ?? null,
        business_type: company.businessType ?? null,
        main_product: company.mainProduct || null,
        company_description: company.companyDescription || null,
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
    if (!data.company.companyName?.trim()) {
      const msg = "회사 이름이 없습니다. 1단계로 돌아가 회사 이름을 입력해 주세요.";
      toast.error(msg);
      setError(msg);
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const result = await prototypeSessions.finalize(token, data.sessionId, {
        project_name: data.company.companyName,
        description: data.company.solutionRequest || null,
      });

      // 가이드 모달 표시를 위해 projectId를 store에 설정 (즉시 라우팅 대신 StepConfirmation이 모달을 보여줌)
      setCreatedProjectId(result.project_id);

      // Linear/Notion 초기 태스크 자동 등록 (실패해도 프로젝트 생성은 완료된 상태)
      const ev = useSolutionWizardStore.getState().data.env.envVars;
      const hasLinear = !!ev["LINEAR_API_KEY"] && !!ev["LINEAR_TEAM_ID"];
      const hasNotion = !!ev["NOTION_API_KEY"] && !!ev["NOTION_DATABASE_ID"];

      if (hasLinear || hasNotion) {
        void integrations
          .registerInitialTasks(token, result.project_id, {
            linear_api_key: hasLinear ? ev["LINEAR_API_KEY"] : null,
            linear_team_id: hasLinear ? ev["LINEAR_TEAM_ID"] : null,
            notion_api_key: hasNotion ? ev["NOTION_API_KEY"] : null,
            notion_database_id: hasNotion ? ev["NOTION_DATABASE_ID"] : null,
            project_name: data.company.companyName,
          })
          .catch(() => {
            // 초기 태스크 등록 실패는 무시 (프로젝트 생성은 성공)
          });
      }
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

  const handleResumeSession = (session: PrototypeSessionResponse) => {
    setSessionId(session.id);
    if (session.status === "completed") {
      goToStep(2);
    } else {
      goToStep(1);
    }
    setShowResumeDialog(false);
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await prototypeSessions.delete(token, sessionId);
      const updated = pendingSessions.filter((s) => s.id !== sessionId);
      setPendingSessions(updated);
      if (updated.length === 0) {
        setShowResumeDialog(false);
      }
    } catch {
      toast.error("세션 삭제 중 오류가 발생했습니다.");
    }
  };

  return (
    <>
    <BaseModal
      open={showResumeDialog}
      onClose={() => setShowResumeDialog(false)}
      title="진행 중인 세션이 있습니다"
      titleId="resume-dialog-title"
      size="md"
    >
      <div className="space-y-4 p-6">
        <p className="text-sm text-zinc-500">
          이전에 시작한 위저드 세션을 계속 진행하거나 새로 시작할 수 있습니다.
        </p>
        <div className="space-y-2">
          {pendingSessions.slice(0, 5).map((s) => (
            <div
              key={s.id}
              className="group flex w-full items-stretch rounded-xl border border-zinc-200 bg-zinc-50 transition-colors hover:border-violet-500/30 hover:bg-violet-500/5"
            >
              <button
                type="button"
                onClick={() => handleResumeSession(s)}
                className="flex min-w-0 flex-1 items-start gap-3 px-4 py-3 text-left"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-zinc-900">
                    {s.solution_prompt
                      ? s.solution_prompt.slice(0, 60) + (s.solution_prompt.length > 60 ? "…" : "")
                      : "(요청 내용 없음)"}
                  </p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className="text-[11px] text-zinc-500">
                      {new Date(s.created_at).toLocaleDateString("ko-KR", {
                        month: "2-digit",
                        day: "2-digit",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                        s.status === "completed"
                          ? "bg-emerald-50 text-emerald-600"
                          : "bg-zinc-100 text-zinc-500",
                      )}
                    >
                      {s.status === "completed"
                        ? "프로토타입 생성됨"
                        : s.status === "generating"
                          ? "생성 중"
                          : "대기 중"}
                    </span>
                  </div>
                </div>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-zinc-400" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => void handleDeleteSession(s.id)}
                className="flex items-center px-3 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500"
                aria-label="세션 삭제"
              >
                <Trash2 className="h-3.5 w-3.5 text-zinc-400 hover:text-red-500" aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setShowResumeDialog(false)}
          className="w-full rounded-xl border border-zinc-200 px-4 py-2.5 text-sm text-zinc-600 transition-colors hover:bg-zinc-50"
        >
          새로 시작
        </button>
      </div>
    </BaseModal>

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
          className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" aria-hidden="true" />
          <p className="flex-1 text-sm text-red-700">{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              void handleStep1Next();
            }}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-600 transition-colors hover:bg-red-100"
          >
            <RefreshCw className="h-3 w-3" />
            재시도
          </button>
        </div>
      )}

      <StepComponent />
    </SolutionWizardLayout>
    </>
  );
}
