export interface CompanyStep {
  companyName: string;
  industry: string;
  techStack: string[];
  mainProduct: string;
  businessType: string;
  solutionPrompt: string;
  enableAutoDecompose: boolean;
}

export interface PrototypeItem {
  id: string;
  variantIndex: number;
  title: string;
  description: string | null;
  isRecommended: boolean;
  pros: string[];
  cons: string[];
}

export interface PrototypesStep {
  selectedPrototypeId: string | null;
  prototypes: PrototypeItem[];
}

export interface PMRecommendItem {
  pmId: string;
  name: string;
  slug: string;
  title: string | null;
  domain: string | null;
  matchScore: number;
  reasoning: string;
}

export interface PMStep {
  selectedPmProfileId: string | null;
  recommendedPMs: PMRecommendItem[];
}

export interface AgentsStep {
  selectedAgents: string[];
  selectedSkills: string[];
  selectedHooks: string[];
}

export interface PlatformStep {
  platformId: string | null;
}

export interface OsStep {
  osId: string | null;
}

export interface EnvStep {
  authMethod: "api_key" | "oauth_browser" | "oauth_setup_token" | null;
  envVars: Record<string, string>;
  deferredEnvVars?: string[];
}

export interface RoiBreakdownItem {
  role_key: string;
  label: string;
  days: number;
  rate: number;
  subtotal: number;
}

export interface RoiCalculateResponse {
  baseline_cost: number;
  clickeye_cost: number;
  savings: number;
  savings_ratio: number;
  baseline_days: number;
  clickeye_days: number;
  breakdown: RoiBreakdownItem[];
  rates_snapshot: Record<string, Record<string, number>>;
  formula_version: string;
}

export interface RoiStep {
  result: RoiCalculateResponse | null;
}

export interface WizardState {
  sessionId: string | null;
  organizationId: string | null;
  currentStep: number;
  company: CompanyStep;
  prototypes: PrototypesStep;
  pm: PMStep;
  agents: AgentsStep;
  platform: PlatformStep;
  os: OsStep;
  env: EnvStep;
  roi: RoiStep;
}

export const INITIAL_WIZARD_STATE: WizardState = {
  sessionId: null,
  organizationId: null,
  currentStep: 0,
  company: {
    companyName: "",
    industry: "",
    techStack: [],
    mainProduct: "",
    businessType: "",
    solutionPrompt: "",
    enableAutoDecompose: true,
  },
  prototypes: {
    selectedPrototypeId: null,
    prototypes: [],
  },
  pm: {
    selectedPmProfileId: null,
    recommendedPMs: [],
  },
  agents: {
    selectedAgents: [],
    selectedSkills: [],
    selectedHooks: [],
  },
  platform: { platformId: null },
  os: { osId: null },
  env: {
    authMethod: null,
    envVars: {},
  },
  roi: { result: null },
};
