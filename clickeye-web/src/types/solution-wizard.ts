/** Solution Wizard v2 타입 정의 */

export const SOLUTION_WIZARD_STEPS = [
  { id: "company", label: "회사 정보", description: "회사 정보와 솔루션 요구사항 입력" },
  { id: "generation", label: "솔루션 생성", description: "AI가 솔루션 프로토타입을 생성합니다" },
  { id: "prototypes", label: "프로토타입", description: "AI가 생성한 솔루션 후보 선택" },
  { id: "pm-recommendation", label: "PM 추천", description: "AI가 최적의 PM을 분석합니다" },
  { id: "pm-selection", label: "PM 선택", description: "프로젝트 매니저 AI 선택" },
  { id: "pm-composition", label: "PM 구성", description: "선택한 PM의 구성 요소 확인" },
  { id: "agents", label: "에이전트", description: "AI 에이전트 구성 확인" },
  { id: "platform", label: "플랫폼", description: "Agent 플랫폼 선택" },
  { id: "os", label: "실행 환경", description: "솔루션을 실행할 OS 환경 선택" },
  { id: "env", label: "환경변수", description: "API 키 및 환경변수 입력" },
  { id: "roi", label: "ROI 비교", description: "ClickEye 도입 효율 가치 산출" },
  { id: "confirm", label: "최종 확인", description: "설정 확인 및 프로젝트 생성" },
] as const;

export type SolutionWizardStepId = (typeof SOLUTION_WIZARD_STEPS)[number]["id"];

/**
 * Modernize 위저드 단계 정의 — 기존 코드 현대화 모드 전용.
 *
 * MVP-2-A 의 M4 에서 실제 step 컴포넌트와 함께 활용된다. M1 에서는 모드 분기만
 * 도입하고 사용처는 아직 없다. 기존 `SOLUTION_WIZARD_STEPS` 는 절대 미변경.
 */
export const MODERNIZE_WIZARD_STEPS = [
  { id: "repo-connect", label: "GitHub 연결", description: "기존 코드베이스를 가져올 GitHub repo 를 연결합니다" },
  { id: "repo-select", label: "저장소 선택", description: "분석할 repo 와 브랜치를 선택합니다" },
  { id: "diagnose", label: "코드 진단", description: "AI 가 코드를 분석합니다" },
  { id: "diagnosis-review", label: "진단 검토", description: "현대화 시나리오와 권장사항을 선택합니다" },
  { id: "pm-recommendation", label: "PM 추천", description: "AI 가 최적의 PM 을 분석합니다" },
  { id: "pm-selection", label: "PM 선택", description: "프로젝트 매니저 AI 선택" },
  { id: "pm-composition", label: "PM 구성", description: "선택한 PM 의 구성 요소 확인" },
  { id: "agents", label: "에이전트", description: "AI 에이전트 구성 확인" },
  { id: "platform", label: "플랫폼", description: "Agent 플랫폼 선택" },
  { id: "env", label: "환경변수", description: "API 키 및 환경변수 입력" },
  { id: "confirm", label: "최종 확인", description: "설정 확인 및 Linear 등록 + ZIP 생성" },
] as const;

export type ModernizeWizardStepId = (typeof MODERNIZE_WIZARD_STEPS)[number]["id"];

/** 위저드 단계 정의의 공통 형태 — getWizardSteps 의 반환 타입 */
export interface WizardStepDef {
  readonly id: string;
  readonly label: string;
  readonly description: string;
}

/**
 * 위저드 모드 — 'new' (기존 7-Step 솔루션 설계) / 'modernize' (기존 코드 현대화).
 * 기본값은 항상 'new'. 기존 호출자는 mode 를 모를 수 있고, 그 경우 자동으로 기존 동작 유지.
 */
export type SolutionWizardMode = "new" | "modernize";

/**
 * 모드에 따라 적절한 STEPS 배열 반환.
 * 기존 `SOLUTION_WIZARD_STEPS` 직접 사용 호출자는 영향 없다 (mode='new' 와 동일 결과).
 */
export function getWizardSteps(
  mode: SolutionWizardMode = "new",
): readonly WizardStepDef[] {
  return mode === "modernize" ? MODERNIZE_WIZARD_STEPS : SOLUTION_WIZARD_STEPS;
}

// ---------------------------------------------------------------------------
// Step 1: 회사 정보
// ---------------------------------------------------------------------------

export type BusinessType = "b2b" | "b2c" | "b2b2c" | "internal";

/** 회사 규모 */
export type CompanySize =
  | "startup"
  | "small"
  | "medium"
  | "mid-large"
  | "enterprise";

/** 업종 */
export type IndustryType =
  | "it"
  | "fintech"
  | "ecommerce"
  | "healthcare"
  | "education"
  | "manufacturing"
  | "logistics"
  | "marketing"
  | "game"
  | "other";

/** 회사 기본 정보 */
export interface CompanyInfo {
  /** 회사명 */
  companyName: string;
  /** 회사 규모 */
  companySize: CompanySize | null;
  /** 업종 */
  industry: IndustryType | null;
  /** 기술 스택 (복수 선택) */
  techStack: string[];
  /** 주력 제품/서비스 */
  mainProduct: string;
  /** 비즈니스 유형 */
  businessType: BusinessType | null;
  /** 회사 설명 (자연어) */
  companyDescription: string;
}

/** 솔루션 요청 프롬프트 (자연어 입력) */
export interface SolutionPrompt {
  /** 필요한 솔루션 설명 텍스트 */
  text: string;
}

/** Step 1 위저드 상태 (회사 정보 + 솔루션 프롬프트 통합) */
export interface CompanyStep extends CompanyInfo {
  /** 필요한 솔루션 설명 (자연어) */
  solutionRequest: string;
  /** ZIP start.sh에 자동 분석/분해(bootstrap_clickeye.sh) 포함 여부. 기본 false. */
  enableAutoDecompose: boolean;
}

// ---------------------------------------------------------------------------
// Step 2: 프로토타입
// ---------------------------------------------------------------------------

/** 프로토타입 UI 메뉴 항목 */
export interface PrototypeUIMenuItem {
  label: string;
  icon?: string;
  path?: string;
}

/** 프로토타입 UI 페이지 정의 */
export interface PrototypeUIPage {
  name: string;
  description?: string;
  components?: string[];
}

/** 프로토타입 UI 컬러 팔레트 */
export interface PrototypeUIColors {
  primary: string;
  secondary?: string;
  accent?: string;
  background?: string;
}

/** 프로토타입 UI 구조 (메뉴/페이지/컬러) */
export interface PrototypeUIStructure {
  menus: PrototypeUIMenuItem[];
  pages: PrototypeUIPage[];
  colors: PrototypeUIColors;
}

/** 프로토타입 후보 */
export interface Prototype {
  id: string;
  name: string;
  solutionType: string;
  reasoning: string | null;
  uiStructure?: PrototypeUIStructure;
  config: Record<string, unknown>;
}

/** @deprecated Use Prototype instead */
export interface PrototypeOption {
  id: string;
  name: string;
  solutionType: string;
  reasoning: string | null;
  config: Record<string, unknown>;
  techStack?: string[];
  architecturePattern?: string;
  rationale?: string;
  isRecommended?: boolean;
  pros?: string[];
  cons?: string[];
  // 정량 지표 (Phase A — 백엔드 PrototypeResponse와 동일 키 사용)
  estimatedWeeksMin?: number | null;
  estimatedWeeksMax?: number | null;
  teamSizeMin?: number | null;
  teamSizeMax?: number | null;
  teamRoles?: string[];
  complexityScore?: number | null;
  scalabilityScore?: number | null;
  monthlyCostMinUsd?: number | null;
  monthlyCostMaxUsd?: number | null;
  maintenanceDifficulty?: string | null;
  skillRequirements?: string[];
  matchReasoning?: string | null;
}

/** Step 2 위저드 상태 */
export interface PrototypesStep {
  /** 선택된 프로토타입 ID */
  selectedPrototypeId: string | null;
  /** 생성된 프로토타입 목록 */
  generatedPrototypes: Prototype[];
}

// ---------------------------------------------------------------------------
// Step 3-4: PM 추천 / PM 선택
// ---------------------------------------------------------------------------

/** PM 추천 항목 (POST /prototype-sessions/{id}/recommend-pms 응답 항목) */
export interface PMRecommendedItem {
  pmId: string;
  name: string;
  slug: string;
  avatarUrl: string | null;
  title: string | null;
  domain: string | null;
  matchScore: number;
  reasoning: string;
  dimensionScores: Record<string, number>;
  matchReasons: string[];
}

/** PM 프로필 (프론트엔드 표현 타입) */
export interface PMProfile {
  id: string;
  name: string;
  slug: string;
  title?: string;
  description: string | null;
  avatarUrl: string | null;
  domain?: string;
  specialties: string[];
  skills: string[];
  experienceAreas: string[];
  personalityTraits: Record<string, unknown>;
  isActive: boolean;
}

/** PM 성과 지표 */
export interface PMMetrics {
  pmProfileId: string;
  totalProjects: number;
  successRate: number;
  avgRating: number;
}

/** PM 구성 항목 단위 */
export interface PMCompositionItem {
  id: string;
  componentType: "agent" | "skill" | "tool";
  componentSlug: string;
  componentName: string;
  config: Record<string, unknown>;
  displayOrder: number;
  isRequired: boolean;
}

/** PM 구성 전체 (에이전트/스킬/도구 조합) */
export interface PMComposition {
  pmProfileId: string;
  items: PMCompositionItem[];
}

/** Step 3-4 위저드 상태 */
export interface PMStep {
  selectedPmProfileId: string | null;
  /** Step 3 (PM 추천) 결과 캐시 — Step 4에서 소비 */
  recommendedItems: PMRecommendedItem[];
  /** 선택된 PM이 지원하는 플랫폼 슬러그 — Step 7 플랫폼 필터링에 사용 */
  pmSupportedPlatforms: string[];
}

// ---------------------------------------------------------------------------
// Step 4~6: 에이전트, 플랫폼, 환경변수
// ---------------------------------------------------------------------------

/** Step 4: 에이전트 구성 */
export interface AgentsStep {
  selectedAgents: string[];
  selectedSkills: string[];
  selectedHooks: string[];
  selectedMcps: string[];
}

/** Step 5: 플랫폼 선택 */
export interface PlatformStep {
  platformId: string | null;
}

/** Step 6: OS 실행 환경 선택 */
export type OsId = "wsl2";

export interface OsStep {
  osId: OsId | null;
}

/** Step 7: 환경변수 */
export type AuthMethod = "api_key" | "oauth_browser";

export interface EnvStep {
  envVars: Record<string, string>;
  authMethod: AuthMethod;
  /** 사용자가 "나중에 입력"을 선택한 키 목록 */
  deferredEnvVars: string[];
}

// ---------------------------------------------------------------------------
// Step 10: ROI 비교
// ---------------------------------------------------------------------------

export interface RoiBreakdownItem {
  role_key: string;
  label: string;
  days: number;
  rate: number;
  subtotal: number;
}

export interface RoiResult {
  baselineCost: number;
  clickeyeCost: number;
  savings: number;
  savingsRatio: number;
  baselineDays: number;
  clickeyeDays: number;
  breakdown: RoiBreakdownItem[];
  ratesSnapshot: Record<string, Record<string, number>>;
  formulaVersion: string;
}

export interface RoiOverrides {
  roleRates?: Record<string, number>;
}

export interface RoiStep {
  overrides: RoiOverrides;
  result: RoiResult | null;
}

// ---------------------------------------------------------------------------
// 위저드 전체 상태
// ---------------------------------------------------------------------------

/** 솔루션 위저드 전체 데이터 */
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
  os: OsStep;
  env: EnvStep;
  roi: RoiStep;
}

export const INITIAL_SOLUTION_WIZARD_DATA: SolutionWizardData = {
  sessionId: null,
  organizationId: null,
  company: {
    companyName: "",
    companySize: null,
    industry: null,
    techStack: [],
    mainProduct: "",
    businessType: null,
    companyDescription: "",
    solutionRequest: "",
    enableAutoDecompose: false,
  },
  prototypes: {
    selectedPrototypeId: null,
    generatedPrototypes: [],
  },
  pm: {
    selectedPmProfileId: null,
    recommendedItems: [],
    pmSupportedPlatforms: [],
  },
  agents: {
    selectedAgents: [],
    selectedSkills: [],
    selectedHooks: [],
    selectedMcps: [],
  },
  platform: {
    platformId: null,
  },
  os: {
    osId: null,
  },
  env: {
    envVars: {},
    authMethod: "api_key",
    deferredEnvVars: [],
  },
  roi: {
    overrides: {},
    result: null,
  },
};

// ---------------------------------------------------------------------------
// Modernize (MVP-2-A) — 기존 코드 현대화 위저드 sub-state
// 기본 mode='new' 일 때는 사용되지 않음. mode='modernize' 일 때만 의미가 있다.
// ---------------------------------------------------------------------------

/** Modernize 시나리오 — VersionUp 우선, 이후 Refactor / LanguageMigrate */
export type ModernizeScenario = "versionup" | "refactor" | "language_migrate";

/** Modernize 위저드 데이터 */
export interface ModernizeData {
  /** GitHubInstallation.id (UUID 문자열) — Step 0 에서 설정 */
  githubInstallationPk: string | null;
  /** GitHub 측 installation id — 표시/검증용 */
  githubInstallationId: number | null;
  /** 선택된 repo (Step 1) */
  repo: {
    fullName: string;
    branch: string;
    /** 옵셔널 monorepo 하위 경로 */
    subpath: string | null;
  } | null;
  /** Step 2 진단 완료 플래그 — 부모가 nextStep() 트리거 */
  diagnoseDone: boolean;
  /** ModernizeSession.id — POST /modernize/sessions 응답에서 설정 */
  sessionId: string | null;
  /** 시나리오 (Step 3) */
  scenario: ModernizeScenario | null;
  /** 사용자가 selected=true 로 유지한 권장안 ID 목록 */
  acceptedRecommendationIds: string[];
}

export const INITIAL_MODERNIZE_DATA: ModernizeData = {
  githubInstallationPk: null,
  githubInstallationId: null,
  repo: null,
  diagnoseDone: false,
  sessionId: null,
  scenario: null,
  acceptedRecommendationIds: [],
};
