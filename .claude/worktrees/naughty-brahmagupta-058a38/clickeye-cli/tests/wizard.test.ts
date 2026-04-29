import { describe, it, expect } from "vitest";
import { defaultProjectInfo } from "../src/wizard/project.js";
import { defaultAgentSelection } from "../src/wizard/agents.js";

describe("wizard/project", () => {
  it("defaultProjectInfo는 올바른 기본값을 반환한다", () => {
    const info = defaultProjectInfo();
    expect(info.name).toBe("my-project");
    expect(info.type).toBe("fullstack");
    expect(info.stack).toBe("fastapi-nextjs");
  });

  it("defaultProjectInfo는 유효한 ProjectInfo 타입이다", () => {
    const info = defaultProjectInfo();
    expect(info).toHaveProperty("name");
    expect(info).toHaveProperty("type");
    expect(info).toHaveProperty("stack");
  });
});

describe("wizard/agents", () => {
  it("defaultAgentSelection은 하네스 에이전트를 필수 포함한다", () => {
    const selection = defaultAgentSelection();
    expect(selection.agents).toContain("harness");
  });

  it("defaultAgentSelection은 backend, frontend를 기본 포함한다", () => {
    const selection = defaultAgentSelection();
    expect(selection.agents).toContain("backend");
    expect(selection.agents).toContain("frontend");
  });

  it("defaultAgentSelection은 배열을 반환한다", () => {
    const selection = defaultAgentSelection();
    expect(Array.isArray(selection.agents)).toBe(true);
    expect(selection.agents.length).toBeGreaterThan(0);
  });
});
