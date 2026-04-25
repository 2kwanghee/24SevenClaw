"use client";

import { useEffect } from "react";
import { Joyride, STATUS, type EventData } from "react-joyride";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { TOUR_STEPS } from "./tour-steps";

export function TourWrapper() {
  const { tourCompleted, tourRunning, setTourCompleted, setTourRunning } =
    useOnboardingStore();

  useEffect(() => {
    if (!tourCompleted) {
      // DOM이 안정화되길 기다린 후 자동 시작
      const timer = setTimeout(() => setTourRunning(true), 500);
      return () => clearTimeout(timer);
    }
  }, [tourCompleted, setTourRunning]);

  const handleEvent = (data: EventData) => {
    const { status } = data;
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setTourCompleted(true);
      setTourRunning(false);
    }
  };

  return (
    <Joyride
      steps={TOUR_STEPS}
      run={tourRunning}
      continuous
      scrollToFirstStep
      onEvent={handleEvent}
      locale={{
        back: "이전",
        close: "닫기",
        last: "완료",
        next: "다음",
        skip: "건너뛰기",
      }}
      options={{
        primaryColor: "#18181b",
        backgroundColor: "#ffffff",
        textColor: "#09090b",
        overlayColor: "rgba(0, 0, 0, 0.4)",
        arrowColor: "#ffffff",
        zIndex: 10000,
        showProgress: true,
        skipBeacon: true,
        buttons: ["back", "primary", "skip"],
        overlayClickAction: false,
      }}
      styles={{
        tooltip: {
          borderRadius: "12px",
          border: "1px solid #e4e4e7",
          boxShadow: "0 8px 32px rgba(0,0,0,0.08)",
          padding: "20px 24px",
        },
        buttonPrimary: {
          borderRadius: "8px",
          padding: "8px 16px",
          fontSize: "13px",
          fontWeight: "500",
        },
        buttonBack: {
          marginRight: "8px",
          fontSize: "13px",
          color: "#52525b",
        },
        buttonSkip: {
          fontSize: "13px",
          color: "#a1a1aa",
        },
      }}
    />
  );
}
