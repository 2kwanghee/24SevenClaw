import type { Step } from "react-joyride";

/** next-intl 의 useTranslations("wizard.tour") 반환 함수 타입 */
type TourTranslator = (key: string) => string;

/**
 * 위저드 투어 스텝 정의 — title/content 는 i18n 메시지에서 가져온다.
 * target/placement 등 구조 정보는 언어와 무관하게 고정.
 */
export function buildWizardTourSteps(t: TourTranslator): Step[] {
  return [
    {
      target: '[data-tour="wizard-stepper"]',
      title: t("steps.progress.title"),
      content: t("steps.progress.content"),
      skipBeacon: true,
      placement: "bottom",
    },
    {
      target: '[data-tour="wizard-content"]',
      title: t("steps.input.title"),
      content: t("steps.input.content"),
      placement: "top",
    },
    {
      target: '[data-tour="wizard-nav"]',
      title: t("steps.navigation.title"),
      content: t("steps.navigation.content"),
      placement: "top",
    },
  ];
}
