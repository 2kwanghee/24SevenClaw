import { describe, expect, it } from "vitest";

import { canProceedAgentsStep, type AgentsStepState } from "../wizard-gates";

const TICKET_SOURCE_IDS = ["linear", "notion"];

const baseAgents = (overrides: Partial<AgentsStepState> = {}): AgentsStepState => ({
  selectedAgents: [],
  selectedSkills: [],
  selectedMcps: [],
  ...overrides,
});

describe("canProceedAgentsStep (Step 6 — 에이전트 단계 게이트)", () => {
  it("selectedAgents 가 비어있으면 false", () => {
    expect(
      canProceedAgentsStep(
        baseAgents({ selectedAgents: [], selectedSkills: ["linear"] }),
        TICKET_SOURCE_IDS,
      ),
    ).toBe(false);
  });

  it("ticket_source 카탈로그 자체가 비어있으면 (에이전트만 있으면) 통과", () => {
    expect(
      canProceedAgentsStep(
        baseAgents({ selectedAgents: ["claude-code-agent"] }),
        [],
      ),
    ).toBe(true);
  });

  it("PM 이 Linear 를 SKILL 로 잠금 → selectedSkills 에 linear 포함 → 통과 (기존)", () => {
    expect(
      canProceedAgentsStep(
        baseAgents({
          selectedAgents: ["claude-code-agent"],
          selectedSkills: ["linear", "ai-critique"],
        }),
        TICKET_SOURCE_IDS,
      ),
    ).toBe(true);
  });

  it("PM 이 Linear 를 MCP SERVER 로만 잠금 → selectedMcps 에 linear → 통과 (사용자 보고 케이스)", () => {
    expect(
      canProceedAgentsStep(
        baseAgents({
          selectedAgents: ["claude-code-agent"],
          selectedSkills: ["ai-critique"], // skill 에는 ticket_source 없음
          selectedMcps: ["linear", "github"], // mcp 에 linear
        }),
        TICKET_SOURCE_IDS,
      ),
    ).toBe(true);
  });

  it("사용자가 Notion 을 SKILL 로 직접 선택 → 통과", () => {
    expect(
      canProceedAgentsStep(
        baseAgents({
          selectedAgents: ["claude-code-agent"],
          selectedSkills: ["notion"],
        }),
        TICKET_SOURCE_IDS,
      ),
    ).toBe(true);
  });

  it("ticket_source 가 어느 컴포넌트 타입에도 없음 → 차단", () => {
    expect(
      canProceedAgentsStep(
        baseAgents({
          selectedAgents: ["claude-code-agent"],
          selectedSkills: ["ai-critique", "tdd"],
          selectedMcps: ["github", "slack"],
        }),
        TICKET_SOURCE_IDS,
      ),
    ).toBe(false);
  });

  it("selectedMcps 가 undefined 여도 selectedSkills 에 ticket_source 있으면 통과 (이전 store fallback)", () => {
    const agents: AgentsStepState = {
      selectedAgents: ["claude-code-agent"],
      selectedSkills: ["linear"],
      // selectedMcps 미설정
    };
    expect(canProceedAgentsStep(agents, TICKET_SOURCE_IDS)).toBe(true);
  });

  it("selectedMcps 가 undefined 이고 selectedSkills 에도 ticket_source 없음 → 차단", () => {
    const agents: AgentsStepState = {
      selectedAgents: ["claude-code-agent"],
      selectedSkills: [],
    };
    expect(canProceedAgentsStep(agents, TICKET_SOURCE_IDS)).toBe(false);
  });
});
