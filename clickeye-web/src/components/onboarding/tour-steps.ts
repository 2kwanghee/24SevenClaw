import type { Step } from "react-joyride";

export const TOUR_STEPS: Step[] = [
  {
    target: '[data-tour="sidebar-nav"]',
    title: "네비게이션 메뉴",
    content:
      "왼쪽 사이드바를 통해 대시보드의 주요 기능으로 빠르게 이동할 수 있습니다.",
    skipBeacon: true,
    placement: "right",
  },
  {
    target: '[data-tour="new-solution-link"]',
    title: "새 솔루션 만들기",
    content:
      "7-Step 위저드를 통해 AI 에이전트 솔루션을 설계하고 ZIP으로 다운로드할 수 있습니다.",
    placement: "right",
  },
  {
    target: '[data-tour="settings-section"]',
    title: "설정 (Linear 연동)",
    content:
      "조직 멤버 관리, Linear 프로젝트 연동 등 팀 설정을 구성할 수 있습니다.",
    placement: "right",
  },
  {
    target: '[data-tour="projects-link"]',
    title: "AI Team",
    content:
      "프로젝트에서 AI Team을 구성하고 자동화 파이프라인을 실행·모니터링합니다.",
    placement: "right",
  },
  {
    target: '[data-tour="help-button"]',
    title: "도움말",
    content:
      "언제든지 여기서 사용 가이드를 보거나 이 튜토리얼을 다시 시작할 수 있습니다.",
    placement: "bottom",
  },
];
