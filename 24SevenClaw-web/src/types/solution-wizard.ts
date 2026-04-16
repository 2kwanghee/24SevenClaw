/** Solution Wizard v2 타입 정의 */

export const SOLUTION_WIZARD_STEPS = [
  { id: "company", label: "회사 정보", description: "회사 정보와 솔루션 요구사항 입력" },
  { id: "prototypes", label: "프로토타입", description: "AI가 생성한 솔루션 후보 선택" },
  { id: "pm", label: "PM 선택", description: "프로젝트 매니저 AI 선택" },
  { id: "agents", label: "에이전트", description: "AI 에이전트 구성 확인" },
  { id: "platform", label: "플랫폼", description: "Agent 플랫폼 선택" },
  { id: "env", label: "환경변수", description: "API 키 및 환경변수 입력" },
  { id: "confirm", label: "최종 확인", description: "설정 확인 및 프로젝트 생성" },
] as const;

export type SolutionWizardStepId = (typeof SOLUTION_WIZARD_STEPS)[number]["id"];

/** Step 1: 회사 정보 + 자연어 입력 */
export type BusinessType = "b2b" | "b2c" | "b2b2c" | "internal";

export interface CompanyStep {
  /** 회사명 */
  companyName: string;
  /** 주력 제품/서비스 */
  mainProduct: string;
  /** 비즈니스 유형 */
  businessType: BusinessType | null;
  /** 회사 설명 (자연어) */
  companyDescription: string;
  /** 필요한 솔루션 설명 (자연어) */
  solutionRequest: string;
}

/** Step 2: 프로토타입 선택 */
export interface PrototypesStep {
  /** 선택된 프로토타입 ID */
  selectedPrototypeId: string | null;
  /** 생성된 프로토타입 목록 */
  generatedPrototypes: PrototypeOption[];
}

export interface PrototypeOption {
  id: string;
  name: string;
  solutionType: string;
  reasoning: string | null;
  config: Record<string, unknown>;
}

/** Step 3: PM 선택 */
export interface PMStep {
  selectedPmProfileId: string | null;
}

/** Step 4: 에이전트 구성 */
export interface AgentsStep {
  selectedAgents: string[];
  selectedSkills: string[];
}

/** Step 5: 플랫폼 선택 */
export interface PlatformStep {
  platformId: string | null;
}

/** Step 6: 환경변수 */
export interface EnvStep {
  envVars: Record<string, string>;
}

/** 위저드 전체 데이터 */
export interface SolutionWizardData {
  /** 현재 세션 ID (Step 1 완료 후 생성) */
  sessionId: string | null;
  /** 조직 ID */
  organizationId: string | null;
  company: CompanyStep;
  prototypes: PrototypesStep;
  pm: PMStep;
  agents: AgentsStep;
  platform: PlatformStep;
  env: EnvStep;
}

export const INITIAL_SOLUTION_WIZARD_DATA: SolutionWizardData = {
  sessionId: null,
  organizationId: null,
  company: {
    companyName: "",
    mainProduct: "",
    businessType: null,
    companyDescription: "",
    solutionRequest: "",
  },
  prototypes: {
    selectedPrototypeId: null,
    generatedPrototypes: [],
  },
  pm: {
    selectedPmProfileId: null,
  },
  agents: {
    selectedAgents: [],
    selectedSkills: [],
  },
  platform: {
    platformId: null,
  },
  env: {
    envVars: {},
  },
};
