import { create } from "zustand";
import { persist } from "zustand/middleware";

interface OnboardingState {
  tourCompleted: boolean;
  tourRunning: boolean;
  setTourCompleted: (completed: boolean) => void;
  setTourRunning: (running: boolean) => void;
  restartTour: () => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set) => ({
      tourCompleted: false,
      tourRunning: false,
      setTourCompleted: (completed) => set({ tourCompleted: completed }),
      setTourRunning: (running) => set({ tourRunning: running }),
      restartTour: () => set({ tourCompleted: false, tourRunning: true }),
    }),
    {
      name: "clickeye-onboarding",
      partialize: (state) => ({
        tourCompleted: state.tourCompleted,
      }),
    },
  ),
);
