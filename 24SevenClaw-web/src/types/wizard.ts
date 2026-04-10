import type { PlatformId } from "@/lib/engine/platforms/types";

/** 7-Step 위저드 타입 정의 */

export const WIZARD_STEPS = [
  { id: "organization", label: "회사 정보", description: "회사 정보 입력" },
  { id: "solution", label: "솔루션 정의", description: "프로젝트와 솔루션 유형 정의" },
  { id: "agents", label: "에이전트", description: "AI 에이전트 선택" },
  { id: "skills", label: "스킬 장착", description: "외부 도구 스킬 연동" },
  { id: "pipelines", label: "파이프라인", description: "자동화 파이프라인 설정" },
  { id: "platform", label: "플랫폼", description: "Agent 플랫폼 선택" },
  { id: "preview", label: "프리뷰", description: "설정 확인 및 다운로드" },
] as const;

export type WizardStepId = (typeof WIZARD_STEPS)[number]["id"];

/** Step 1: 회사 정보 */
export type CompanySize = "solo" | "small" | "medium" | "enterprise";
export type Industry =
  | "it"
  | "finance"
  | "commerce"
  | "healthcare"
  | "education"
  | "other";

export interface OrganizationStep {
  companyName: string;
  companySize: CompanySize | null;
  industry: Industry | null;
  techStack: string[];
}

/** Step 2: 솔루션 정의 */
export type SolutionType =
  | "saas"
  | "rest-api"
  | "fullstack"
  | "internal-tool"
  | "mvp"
  | "custom";

export interface SolutionStep {
  projectName: string;
  solutionType: SolutionType | null;
  stackPreset: string | null;
  description: string;
}

/** Step 3: 에이전트 선택 */
export interface AgentsStep {
  selectedAgents: string[];
}

/** Step 4: 스킬 장착 */
export interface SkillSelection {
  id: string;
  apiKey?: string;
}

export interface SkillsStep {
  selectedSkills: SkillSelection[];
}

/** Step 5: 파이프라인 */
export interface PipelinesStep {
  selectedPipelines: string[];
}

/** Step 6: 플랫폼 선택 */
export interface PlatformStep {
  platformId: PlatformId | null;
}

/** 추천 결과 (API 응답에서 ID + reasoning 추출) */
export interface Recommendations {
  agents: string[];
  skills: string[];
  pipelines: string[];
  /** 항목별 추천 사유 (ID → reasoning 문장) */
  skillReasonings: Record<string, string>;
  pipelineReasonings: Record<string, string>;
  summary: string;
}

/** 위저드 전체 데이터 */
export interface WizardData {
  organization: OrganizationStep;
  solution: SolutionStep;
  agents: AgentsStep;
  skills: SkillsStep;
  pipelines: PipelinesStep;
  platform: PlatformStep;
}

export const INITIAL_WIZARD_DATA: WizardData = {
  organization: {
    companyName: "",
    companySize: null,
    industry: null,
    techStack: [],
  },
  solution: {
    projectName: "",
    solutionType: null,
    stackPreset: null,
    description: "",
  },
  agents: { selectedAgents: [] },
  skills: { selectedSkills: [] },
  pipelines: { selectedPipelines: [] },
  platform: { platformId: null },
};
