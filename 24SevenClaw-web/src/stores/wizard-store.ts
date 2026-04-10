import { create } from "zustand";

import {
  WIZARD_STEPS,
  INITIAL_WIZARD_DATA,
  type WizardData,
  type OrganizationStep,
  type SolutionStep,
  type AgentsStep,
  type SkillsStep,
  type PipelinesStep,
  type PlatformStep,
  type Recommendations,
} from "@/types/wizard";

export { WIZARD_STEPS, type WizardStepId } from "@/types/wizard";

interface WizardState {
  currentStep: number;
  data: WizardData;
  recommendations: Recommendations | null;
}

interface WizardActions {
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: number) => void;
  setOrganization: (data: Partial<OrganizationStep>) => void;
  setSolution: (data: Partial<SolutionStep>) => void;
  setAgents: (data: AgentsStep) => void;
  setSkills: (data: SkillsStep) => void;
  setPipelines: (data: PipelinesStep) => void;
  setPlatform: (data: PlatformStep) => void;
  setRecommendations: (rec: Recommendations) => void;
  reset: () => void;
}

const initialState: WizardState = {
  currentStep: 0,
  data: INITIAL_WIZARD_DATA,
  recommendations: null,
};

export const useWizardStore = create<WizardState & WizardActions>((set) => ({
  ...initialState,

  nextStep: () =>
    set((state) => ({
      currentStep: Math.min(state.currentStep + 1, WIZARD_STEPS.length - 1),
    })),

  prevStep: () =>
    set((state) => ({
      currentStep: Math.max(state.currentStep - 1, 0),
    })),

  goToStep: (step) =>
    set({ currentStep: Math.max(0, Math.min(step, WIZARD_STEPS.length - 1)) }),

  setOrganization: (org) =>
    set((state) => ({
      data: {
        ...state.data,
        organization: { ...state.data.organization, ...org },
      },
    })),

  setSolution: (sol) =>
    set((state) => ({
      data: {
        ...state.data,
        solution: { ...state.data.solution, ...sol },
      },
    })),

  setAgents: (agents) =>
    set((state) => ({ data: { ...state.data, agents } })),

  setSkills: (skills) =>
    set((state) => ({ data: { ...state.data, skills } })),

  setPipelines: (pipelines) =>
    set((state) => ({ data: { ...state.data, pipelines } })),

  setPlatform: (platform) =>
    set((state) => ({ data: { ...state.data, platform } })),

  setRecommendations: (rec) => set({ recommendations: rec }),

  reset: () => set(initialState),
}));
