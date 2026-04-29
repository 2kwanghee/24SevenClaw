import { create } from "zustand";
import { persist } from "zustand/middleware";

interface OnboardingState {
  tourCompleted: boolean;
  tourRunning: boolean;
  wizardTourCompleted: boolean;
  wizardTourRunning: boolean;
  setTourCompleted: (completed: boolean) => void;
  setTourRunning: (running: boolean) => void;
  restartTour: () => void;
  setWizardTourCompleted: (completed: boolean) => void;
  setWizardTourRunning: (running: boolean) => void;
  restartWizardTour: () => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      tourCompleted: false,
      tourRunning: false,
      wizardTourCompleted: false,
      wizardTourRunning: false,
      setTourCompleted: (completed) => set({ tourCompleted: completed }),
      setTourRunning: (running) => set({ tourRunning: running }),
      restartTour: () => set({ tourCompleted: false, tourRunning: true }),
      setWizardTourCompleted: (completed) => set({ wizardTourCompleted: completed }),
      setWizardTourRunning: (running) => set({ wizardTourRunning: running }),
      restartWizardTour: () => set({ wizardTourCompleted: false, wizardTourRunning: true }),
    }),
    {
      name: "clickeye-onboarding",
      partialize: (state) => ({
        tourCompleted: state.tourCompleted,
        wizardTourCompleted: state.wizardTourCompleted,
      }),
    },
  ),
);
