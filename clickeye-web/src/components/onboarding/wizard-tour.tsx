"use client";

import { useEffect } from "react";
import { Joyride, STATUS, type EventData } from "react-joyride";
import { useTranslations } from "next-intl";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { buildWizardTourSteps } from "./wizard-tour-steps";

export function WizardTourWrapper() {
  const t = useTranslations("wizard.tour");
  const {
    wizardTourCompleted,
    wizardTourRunning,
    setWizardTourCompleted,
    setWizardTourRunning,
  } = useOnboardingStore();

  useEffect(() => {
    if (!wizardTourCompleted) {
      const timer = setTimeout(() => setWizardTourRunning(true), 600);
      return () => clearTimeout(timer);
    }
  }, [wizardTourCompleted, setWizardTourRunning]);

  const handleEvent = (data: EventData) => {
    const { status } = data;
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setWizardTourCompleted(true);
      setWizardTourRunning(false);
    }
  };

  return (
    <Joyride
      steps={buildWizardTourSteps(t)}
      run={wizardTourRunning}
      continuous
      scrollToFirstStep
      onEvent={handleEvent}
      locale={{
        back: t("locale.back"),
        close: t("locale.close"),
        last: t("locale.last"),
        next: t("locale.next"),
        skip: t("locale.skip"),
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
