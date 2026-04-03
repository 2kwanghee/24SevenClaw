import { describe, it, expect } from "vitest";
import { generateSkillFiles, getSelectedSkills } from "../src/generators/skill.js";
import type { InitOptions } from "../src/types.js";

const BASE_OPTIONS: InitOptions = {
  project: {
    name: "test-project",
    type: "fullstack",
    stack: "fastapi-nextjs",
  },
  agents: {
    agents: ["backend", "frontend", "harness"],
  },
  workflows: {
    workflows: ["tdd", "harness-gate"],
  },
};

describe("generators/skill", () => {
  it("선택된 워크플로우에 맞는 스킬 파일을 생성한다", async () => {
    const files = await generateSkillFiles(BASE_OPTIONS);

    expect(files.length).toBe(2);

    const paths = files.map((f) => f.relativePath);
    expect(paths).toContain(".claude/skills/tdd-smart-coding.md");
    expect(paths).toContain(".claude/skills/harness-gate.md");
  });

  it("워크플로우 미선택 시 빈 배열을 반환한다", async () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      workflows: { workflows: [] },
    };
    const files = await generateSkillFiles(options);
    expect(files.length).toBe(0);
  });

  it("workflows 미지정 시 빈 배열을 반환한다", async () => {
    const options: InitOptions = {
      project: BASE_OPTIONS.project,
      agents: BASE_OPTIONS.agents,
    };
    const files = await generateSkillFiles(options);
    expect(files.length).toBe(0);
  });

  it("스킬 파일에 스택 정보가 포함된다", async () => {
    const files = await generateSkillFiles(BASE_OPTIONS);
    const tddFile = files.find((f) =>
      f.relativePath.includes("tdd-smart-coding")
    );
    expect(tddFile).toBeDefined();
    expect(tddFile!.content).toContain("pytest");
  });

  it("모든 워크플로우 선택 시 5개 스킬 파일을 생성한다", async () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      workflows: {
        workflows: ["tdd", "ai-critique", "linear", "ralph-loop", "harness-gate"],
      },
    };
    const files = await generateSkillFiles(options);
    expect(files.length).toBe(5);
  });

  it("getSelectedSkills는 올바른 스킬 목록을 반환한다", () => {
    const skills = getSelectedSkills(BASE_OPTIONS);
    expect(skills.length).toBe(2);
    expect(skills.map((s) => s.id)).toEqual(
      expect.arrayContaining(["tdd", "harness-gate"])
    );
  });
});
