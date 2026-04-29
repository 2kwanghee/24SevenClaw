import type { Step } from "react-joyride";

export const WIZARD_TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="wizard-stepper"]',
    title: "진행 단계 표시",
    content:
      "총 10단계로 구성된 위저드입니다. 완료된 단계를 클릭해 언제든지 돌아가 수정할 수 있습니다.",
    skipBeacon: true,
    placement: "bottom",
  },
  {
    target: '[data-tour="wizard-content"]',
    title: "단계별 입력",
    content:
      "회사 정보부터 에이전트 구성, 환경변수 설정까지 각 단계에서 AI 솔루션 설계에 필요한 정보를 입력합니다.",
    placement: "top",
  },
  {
    target: '[data-tour="wizard-nav"]',
    title: "단계 이동",
    content:
      "이전 단계로 돌아가거나 다음으로 진행할 수 있습니다. 필수 항목을 모두 채우면 다음 버튼이 활성화됩니다.",
    placement: "top",
  },
];
