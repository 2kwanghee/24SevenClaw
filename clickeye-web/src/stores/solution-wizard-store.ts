import { create } from "zustand";

import {
  SOLUTION_WIZARD_STEPS,
  INITIAL_SOLUTION_WIZARD_DATA,
  type SolutionWizardData,
  type SolutionWizardStepId,
  type SolutionWizardMode,
  type CompanyStep,
  type PrototypesStep,
  type PMStep,
  type PMRecommendedItem,
  type AgentsStep,
  type PlatformStep,
  type OsStep,
  type EnvStep,
  type RoiStep,
  type PrototypeOption,
} from "@/types/solution-wizard";

export { SOLUTION_WIZARD_STEPS, type SolutionWizardStepId } from "@/types/solution-wizard";
export { type SolutionWizardMode } from "@/types/solution-wizard";

type ValidationStatus = "idle" | "loading" | "valid" | "invalid";

export interface EnvValidationState {
  linearStatus: ValidationStatus;
  linearMessage: string;
  notionStatus: ValidationStatus;
  notionMessage: string;
}

interface SolutionWizardState {
  currentStep: number;
  data: SolutionWizardData;
  isGenerating: boolean;
  /**
   * 위저드 모드 — 'new' (기존 7-Step 솔루션 설계) / 'modernize' (기존 코드 현대화).
   * 기본값 'new'. 기존 모든 사용처는 mode 를 모르더라도 'new' 동작 유지.
   */
  mode: SolutionWizardMode;
  /** Step 0 폼의 유효성 (formState.isValid 동기화) — canProceed 판단에 사용 */
  step0Valid: boolean;
  /** Step 1 (프로토타입 생성) 완료 플래그 — 부모가 감시해서 nextStep() 호출 */
  step1Done: boolean;
  /** Step 3 (PM 추천) 완료 플래그 — 부모가 감시해서 nextStep() 호출 */
  step3Done: boolean;
  /** 프로젝트 생성 완료 후 설정 — StepConfirmation에서 가이드 모달 트리거에 사용 */
  createdProjectId: string | null;
  /** Step 8 (환경변수) Linear/Notion API 키 검증 상태 */
  envValidation: EnvValidationState;
  /** 라이브 프리뷰 — step별 Claude 분석 결과 */
  previewByStep: Partial<Record<SolutionWizardStepId, Record<string, unknown>>>;
  /** 현재 프리뷰 로딩 중인 step */
  previewLoadingStep: SolutionWizardStepId | null;
  /** step별 프리뷰 에러 메시지 */
  previewErrorByStep: Partial<Record<SolutionWizardStepId, string>>;
  /** 모바일 프리뷰 패널 열림 상태 */
  previewPanelOpen: boolean;
}

interface SolutionWizardActions {
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: number) => void;
  /** 위저드 모드 변경 ('new' ↔ 'modernize'). M4 진입점에서 호출 */
  setMode: (mode: SolutionWizardMode) => void;
  setCompany: (data: Partial<CompanyStep>) => void;
  setStep0Valid: (valid: boolean) => void;
  setStep1Done: (done: boolean) => void;
  setStep3Done: (done: boolean) => void;
  setSessionId: (sessionId: string) => void;
  setOrganizationId: (organizationId: string) => void;
  setPrototypes: (data: Partial<PrototypesStep>) => void;
  selectPrototype: (prototypeId: string) => void;
  setGeneratedPrototypes: (prototypes: PrototypeOption[]) => void;
  setPM: (data: Partial<PMStep>) => void;
  setRecommendedPMItems: (items: PMRecommendedItem[]) => void;
  setAgents: (data: AgentsStep) => void;
  setPlatform: (data: PlatformStep) => void;
  setOs: (data: OsStep) => void;
  setEnv: (data: Partial<EnvStep>) => void;
  setRoi: (data: Partial<RoiStep>) => void;
  setIsGenerating: (v: boolean) => void;
  setCreatedProjectId: (id: string) => void;
  setEnvValidation: (data: Partial<EnvValidationState>) => void;
  setPreview: (step: SolutionWizardStepId, data: Record<string, unknown>) => void;
  setPreviewLoading: (step: SolutionWizardStepId | null) => void;
  setPreviewError: (step: SolutionWizardStepId, message: string | null) => void;
  togglePreviewPanel: () => void;
  reset: () => void;
}

const initialState: SolutionWizardState = {
  currentStep: 0,
  data: INITIAL_SOLUTION_WIZARD_DATA,
  isGenerating: false,
  mode: "new",
  step0Valid: false,
  step1Done: false,
  step3Done: false,
  createdProjectId: null,
  envValidation: {
    linearStatus: "idle",
    linearMessage: "",
    notionStatus: "idle",
    notionMessage: "",
  },
  previewByStep: {},
  previewLoadingStep: null,
  previewErrorByStep: {},
  previewPanelOpen: false,
};

export const useSolutionWizardStore = create<
  SolutionWizardState & SolutionWizardActions
>((set) => ({
  ...initialState,

  nextStep: () =>
    set((state) => ({
      currentStep: Math.min(
        state.currentStep + 1,
        SOLUTION_WIZARD_STEPS.length - 1,
      ),
    })),

  prevStep: () =>
    set((state) => {
      const next = Math.max(state.currentStep - 1, 0);
      return {
        currentStep: next,
        // 자동 진행 스텝으로 돌아갈 때 완료 플래그 리셋 → 자동 전진 방지
        ...(next === 1 ? { step1Done: false } : {}),
        ...(next === 3 ? { step3Done: false } : {}),
      };
    }),

  goToStep: (step) =>
    set({
      currentStep: Math.max(
        0,
        Math.min(step, SOLUTION_WIZARD_STEPS.length - 1),
      ),
    }),

  setMode: (mode) => set({ mode }),

  setCompany: (company) =>
    set((state) => ({
      data: {
        ...state.data,
        company: { ...state.data.company, ...company },
      },
    })),

  setStep0Valid: (step0Valid) => set({ step0Valid }),
  setStep1Done: (step1Done) => set({ step1Done }),
  setStep3Done: (step3Done) => set({ step3Done }),

  setSessionId: (sessionId) =>
    set((state) => ({ data: { ...state.data, sessionId } })),

  setOrganizationId: (organizationId) =>
    set((state) => ({ data: { ...state.data, organizationId } })),

  setPrototypes: (prototypes) =>
    set((state) => ({
      data: {
        ...state.data,
        prototypes: { ...state.data.prototypes, ...prototypes },
      },
    })),

  selectPrototype: (prototypeId) =>
    set((state) => ({
      data: {
        ...state.data,
        prototypes: {
          ...state.data.prototypes,
          selectedPrototypeId: prototypeId,
        },
      },
    })),

  setGeneratedPrototypes: (prototypes) =>
    set((state) => ({
      data: {
        ...state.data,
        prototypes: {
          ...state.data.prototypes,
          generatedPrototypes: Array.from(
            new Map(prototypes.map((p) => [p.id, p])).values()
          ),
        },
      },
    })),

  setPM: (pm) =>
    set((state) => ({
      data: { ...state.data, pm: { ...state.data.pm, ...pm } },
    })),

  setRecommendedPMItems: (items) =>
    set((state) => ({
      data: {
        ...state.data,
        pm: { ...state.data.pm, recommendedItems: items },
      },
    })),

  setAgents: (agents) =>
    set((state) => ({ data: { ...state.data, agents } })),

  setPlatform: (platform) =>
    set((state) => ({ data: { ...state.data, platform } })),

  setOs: (os) =>
    set((state) => ({ data: { ...state.data, os } })),

  setEnv: (env) =>
    set((state) => ({
      data: { ...state.data, env: { ...state.data.env, ...env } },
    })),

  setRoi: (roi) =>
    set((state) => ({
      data: { ...state.data, roi: { ...state.data.roi, ...roi } },
    })),

  setIsGenerating: (isGenerating) => set({ isGenerating }),

  setCreatedProjectId: (createdProjectId) => set({ createdProjectId }),

  setEnvValidation: (data) =>
    set((state) => ({
      envValidation: { ...state.envValidation, ...data },
    })),

  setPreview: (step, data) =>
    set((state) => ({
      previewByStep: { ...state.previewByStep, [step]: data },
      previewErrorByStep: { ...state.previewErrorByStep, [step]: undefined },
    })),

  setPreviewLoading: (step) => set({ previewLoadingStep: step }),

  setPreviewError: (step, message) =>
    set((state) => ({
      previewErrorByStep: {
        ...state.previewErrorByStep,
        [step]: message ?? undefined,
      },
      previewLoadingStep: null,
    })),

  togglePreviewPanel: () =>
    set((state) => ({ previewPanelOpen: !state.previewPanelOpen })),

  reset: () => set(initialState),
}));
