import { create } from "zustand";

import {
  SOLUTION_WIZARD_STEPS,
  INITIAL_SOLUTION_WIZARD_DATA,
  type SolutionWizardData,
  type CompanyStep,
  type PrototypesStep,
  type PMStep,
  type AgentsStep,
  type PlatformStep,
  type EnvStep,
  type PrototypeOption,
} from "@/types/solution-wizard";

export { SOLUTION_WIZARD_STEPS, type SolutionWizardStepId } from "@/types/solution-wizard";

interface SolutionWizardState {
  currentStep: number;
  data: SolutionWizardData;
  isGenerating: boolean;
}

interface SolutionWizardActions {
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: number) => void;
  setCompany: (data: Partial<CompanyStep>) => void;
  setSessionId: (sessionId: string) => void;
  setOrganizationId: (organizationId: string) => void;
  setPrototypes: (data: Partial<PrototypesStep>) => void;
  selectPrototype: (prototypeId: string) => void;
  setGeneratedPrototypes: (prototypes: PrototypeOption[]) => void;
  setPM: (data: PMStep) => void;
  setAgents: (data: AgentsStep) => void;
  setPlatform: (data: PlatformStep) => void;
  setEnv: (data: Partial<EnvStep>) => void;
  setIsGenerating: (v: boolean) => void;
  reset: () => void;
}

const initialState: SolutionWizardState = {
  currentStep: 0,
  data: INITIAL_SOLUTION_WIZARD_DATA,
  isGenerating: false,
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
    set((state) => ({
      currentStep: Math.max(state.currentStep - 1, 0),
    })),

  goToStep: (step) =>
    set({
      currentStep: Math.max(
        0,
        Math.min(step, SOLUTION_WIZARD_STEPS.length - 1),
      ),
    }),

  setCompany: (company) =>
    set((state) => ({
      data: {
        ...state.data,
        company: { ...state.data.company, ...company },
      },
    })),

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
          generatedPrototypes: prototypes,
        },
      },
    })),

  setPM: (pm) =>
    set((state) => ({ data: { ...state.data, pm } })),

  setAgents: (agents) =>
    set((state) => ({ data: { ...state.data, agents } })),

  setPlatform: (platform) =>
    set((state) => ({ data: { ...state.data, platform } })),

  setEnv: (env) =>
    set((state) => ({
      data: { ...state.data, env: { ...state.data.env, ...env } },
    })),

  setIsGenerating: (isGenerating) => set({ isGenerating }),

  reset: () => set(initialState),
}));
