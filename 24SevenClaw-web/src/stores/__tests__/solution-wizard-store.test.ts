/**
 * Solution Wizard Store — E2E 플로우 테스트
 *
 * 전체 7단계 위저드의 상태 전이를 검증한다.
 * - 각 단계 데이터 저장
 * - 다음/이전 이동
 * - 마지막 단계 제출 전 모든 데이터 유지
 * - reset 시 초기 상태 복원
 */

import { describe, it, expect, beforeEach } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useSolutionWizardStore } from "../solution-wizard-store";
import { SOLUTION_WIZARD_STEPS } from "@/types/solution-wizard";

/* ───── 헬퍼 ───── */

function getStore() {
  return renderHook(() => useSolutionWizardStore());
}

/* ───── 테스트 ───── */

describe("solution-wizard-store — 7단계 E2E 플로우", () => {
  beforeEach(() => {
    // 각 테스트 전 스토어 초기화
    const { result } = getStore();
    act(() => result.current.reset());
  });

  // ── 1단계: 회사 정보 ──────────────────────────────────────────────────────

  it("Step 0: 초기 상태는 currentStep=0, company 필드 모두 빈 값", () => {
    const { result } = getStore();
    expect(result.current.currentStep).toBe(0);
    expect(result.current.data.company.companyName).toBe("");
    expect(result.current.data.company.businessType).toBeNull();
  });

  it("Step 0: setCompany로 회사 정보 저장", () => {
    const { result } = getStore();

    act(() =>
      result.current.setCompany({
        companyName: "테스트 회사",
        mainProduct: "HR 플랫폼",
        businessType: "b2b",
        companyDescription: "기업용 HR SaaS",
        solutionRequest: "자동화된 채용 관리 시스템이 필요합니다.",
      })
    );

    expect(result.current.data.company.companyName).toBe("테스트 회사");
    expect(result.current.data.company.businessType).toBe("b2b");
    expect(result.current.data.company.solutionRequest).toBe(
      "자동화된 채용 관리 시스템이 필요합니다."
    );
  });

  it("Step 0 → 1: nextStep으로 currentStep 증가", () => {
    const { result } = getStore();

    act(() => result.current.nextStep());

    expect(result.current.currentStep).toBe(1);
  });

  // ── 2단계: 프로토타입 선택 ──────────────────────────────────────────────

  it("Step 1: 세션 ID / 조직 ID 저장", () => {
    const { result } = getStore();

    act(() => {
      result.current.nextStep(); // → step 1
      result.current.setSessionId("session-123");
      result.current.setOrganizationId("org-456");
    });

    expect(result.current.data.sessionId).toBe("session-123");
    expect(result.current.data.organizationId).toBe("org-456");
  });

  it("Step 1: 생성된 프로토타입 목록 저장 후 선택", () => {
    const { result } = getStore();

    const mockPrototypes = [
      { id: "proto-1", name: "CRM 자동화", solutionType: "saas", reasoning: null, config: {} },
      { id: "proto-2", name: "HR 대시보드", solutionType: "internal-tool", reasoning: "내부 운영에 최적", config: {} },
    ];

    act(() => {
      result.current.nextStep();
      result.current.setGeneratedPrototypes(mockPrototypes);
      result.current.selectPrototype("proto-1");
    });

    expect(result.current.data.prototypes.generatedPrototypes).toHaveLength(2);
    expect(result.current.data.prototypes.selectedPrototypeId).toBe("proto-1");
  });

  // ── 3단계: PM 선택 ──────────────────────────────────────────────────────

  it("Step 2: PM 프로필 선택 저장", () => {
    const { result } = getStore();

    act(() => {
      result.current.nextStep();
      result.current.nextStep(); // → step 2
      result.current.setPM({ selectedPmProfileId: "pm-abc" });
    });

    expect(result.current.currentStep).toBe(2);
    expect(result.current.data.pm.selectedPmProfileId).toBe("pm-abc");
  });

  // ── 4단계: 에이전트 구성 ────────────────────────────────────────────────

  it("Step 3: 에이전트 및 스킬 선택 저장", () => {
    const { result } = getStore();

    act(() => {
      result.current.nextStep();
      result.current.nextStep();
      result.current.nextStep(); // → step 3
      result.current.setAgents({
        selectedAgents: ["frontend", "backend", "qa"],
        selectedSkills: ["linear", "github"],
      });
    });

    expect(result.current.data.agents.selectedAgents).toEqual([
      "frontend",
      "backend",
      "qa",
    ]);
    expect(result.current.data.agents.selectedSkills).toEqual([
      "linear",
      "github",
    ]);
  });

  // ── 5단계: 플랫폼 선택 ──────────────────────────────────────────────────

  it("Step 4: 플랫폼 선택 저장", () => {
    const { result } = getStore();

    act(() => {
      for (let i = 0; i < 4; i++) result.current.nextStep(); // → step 4
      result.current.setPlatform({ platformId: "claude-code" });
    });

    expect(result.current.currentStep).toBe(4);
    expect(result.current.data.platform.platformId).toBe("claude-code");
  });

  // ── 6단계: 환경변수 ─────────────────────────────────────────────────────

  it("Step 5: 환경변수 저장", () => {
    const { result } = getStore();

    act(() => {
      for (let i = 0; i < 5; i++) result.current.nextStep(); // → step 5
      result.current.setEnv({
        envVars: { OPENAI_API_KEY: "sk-test", SLACK_TOKEN: "xoxb-test" },
      });
    });

    expect(result.current.data.env.envVars).toEqual({
      OPENAI_API_KEY: "sk-test",
      SLACK_TOKEN: "xoxb-test",
    });
  });

  // ── 7단계: 최종 확인 ────────────────────────────────────────────────────

  it("Step 6: 마지막 단계 도달 후 모든 데이터 유지", () => {
    const { result } = getStore();

    act(() => {
      // 전체 데이터 구성
      result.current.setCompany({
        companyName: "테스트 회사",
        mainProduct: "HR 플랫폼",
        businessType: "b2b",
        companyDescription: "",
        solutionRequest: "채용 자동화 시스템이 필요합니다.",
      });
      result.current.setGeneratedPrototypes([
        { id: "proto-1", name: "CRM", solutionType: "saas", reasoning: null, config: {} },
      ]);
      result.current.selectPrototype("proto-1");
      result.current.setPM({ selectedPmProfileId: "pm-abc" });
      result.current.setAgents({ selectedAgents: ["frontend"], selectedSkills: [] });
      result.current.setPlatform({ platformId: "claude-code" });
      result.current.setEnv({ envVars: { API_KEY: "secret" } });

      // 마지막 단계로 이동
      for (let i = 0; i < SOLUTION_WIZARD_STEPS.length - 1; i++) {
        result.current.nextStep();
      }
    });

    const { currentStep, data } = result.current;
    expect(currentStep).toBe(SOLUTION_WIZARD_STEPS.length - 1);
    expect(data.company.companyName).toBe("테스트 회사");
    expect(data.prototypes.selectedPrototypeId).toBe("proto-1");
    expect(data.pm.selectedPmProfileId).toBe("pm-abc");
    expect(data.agents.selectedAgents).toContain("frontend");
    expect(data.platform.platformId).toBe("claude-code");
    expect(data.env.envVars.API_KEY).toBe("secret");
  });

  it("Step 6: nextStep은 마지막 단계를 초과하지 않음", () => {
    const { result } = getStore();

    act(() => {
      for (let i = 0; i < 20; i++) result.current.nextStep();
    });

    expect(result.current.currentStep).toBe(SOLUTION_WIZARD_STEPS.length - 1);
  });

  // ── 이전/건너뛰기 ────────────────────────────────────────────────────────

  it("Step 0에서 prevStep은 step을 0 미만으로 내리지 않음", () => {
    const { result } = getStore();

    act(() => result.current.prevStep());

    expect(result.current.currentStep).toBe(0);
  });

  it("goToStep으로 임의 단계 이동", () => {
    const { result } = getStore();

    act(() => result.current.goToStep(3));

    expect(result.current.currentStep).toBe(3);
  });

  // ── reset ─────────────────────────────────────────────────────────────────

  it("reset 시 초기 상태로 복원", () => {
    const { result } = getStore();

    act(() => {
      result.current.setCompany({ companyName: "테스트", mainProduct: "제품" });
      result.current.nextStep();
      result.current.nextStep();
      result.current.reset();
    });

    expect(result.current.currentStep).toBe(0);
    expect(result.current.data.company.companyName).toBe("");
    expect(result.current.data.sessionId).toBeNull();
  });

  // ── isGenerating ──────────────────────────────────────────────────────────

  it("setIsGenerating으로 생성 상태 토글", () => {
    const { result } = getStore();

    act(() => result.current.setIsGenerating(true));
    expect(result.current.isGenerating).toBe(true);

    act(() => result.current.setIsGenerating(false));
    expect(result.current.isGenerating).toBe(false);
  });
});
