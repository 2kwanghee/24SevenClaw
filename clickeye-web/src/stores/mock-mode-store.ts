import { create } from "zustand";
import { persist } from "zustand/middleware";

interface MockModeState {
  enabled: boolean;
  toggle: () => void;
  setEnabled: (v: boolean) => void;
}

/**
 * 딜리버리 콘솔 목업(샘플) 데이터 표시 여부를 관리하는 UI 상태 스토어.
 * 서버 데이터가 아닌 순수 클라이언트 UI 토글이므로 Zustand + persist 사용.
 * localStorage 키: "delivery-mock". 기본값 OFF(회귀 0).
 */
export const useMockMode = create<MockModeState>()(
  persist(
    (set) => ({
      enabled: false,
      toggle: () => set((s) => ({ enabled: !s.enabled })),
      setEnabled: (v) => set({ enabled: v }),
    }),
    {
      name: "delivery-mock",
      partialize: (state) => ({ enabled: state.enabled }),
    },
  ),
);
