import { describe, it, expect } from "vitest";
import { generateHookFiles } from "../src/generators/hook.js";
import { generateSettings } from "../src/generators/settings.js";
import { generateScriptFiles } from "../src/generators/scripts.js";
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

describe("generators/hook", () => {
  it("harness-gate 선택 시 harness-gate.sh를 생성한다", async () => {
    const files = await generateHookFiles(BASE_OPTIONS);
    expect(files.length).toBe(1);
    expect(files[0].relativePath).toBe("scripts/harness-gate.sh");
  });

  it("harness-gate.sh에 스택별 Gate 명령어가 포함된다", async () => {
    const files = await generateHookFiles(BASE_OPTIONS);
    const content = files[0].content;

    // fastapi-nextjs 스택의 명령어 확인
    expect(content).toContain("ruff check");
    expect(content).toContain("mypy");
    expect(content).toContain("pytest");
    expect(content).toContain("npm run lint");
    expect(content).toContain("tsc --noEmit");
  });

  it("harness-gate 미선택 시 빈 배열을 반환한다", async () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      workflows: { workflows: ["tdd"] },
    };
    const files = await generateHookFiles(options);
    expect(files.length).toBe(0);
  });

  it("django-react 스택에서 올바른 Gate 명령어를 생성한다", async () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      project: { ...BASE_OPTIONS.project, stack: "django-react" },
    };
    const files = await generateHookFiles(options);
    expect(files[0].content).toContain("ruff check");
    expect(files[0].content).toContain("mypy");
  });

  it("express-vue 스택에서 올바른 Gate 명령어를 생성한다", async () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      project: { ...BASE_OPTIONS.project, stack: "express-vue" },
    };
    const files = await generateHookFiles(options);
    expect(files[0].content).toContain("eslint");
    expect(files[0].content).toContain("npm run lint");
  });
});

describe("generators/settings — Hook 등록", () => {
  it("harness-gate 선택 시 UserPromptSubmit Hook이 등록된다", () => {
    const file = generateSettings(BASE_OPTIONS);
    const parsed = JSON.parse(file.content);

    expect(parsed.hooks.UserPromptSubmit.length).toBeGreaterThan(0);
    expect(parsed.hooks.UserPromptSubmit[0].command).toContain("harness-gate.sh");
  });

  it("harness-gate 미선택 시 UserPromptSubmit Hook이 비어있다", () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      workflows: { workflows: ["tdd"] },
    };
    const file = generateSettings(options);
    const parsed = JSON.parse(file.content);

    expect(parsed.hooks.UserPromptSubmit.length).toBe(0);
  });

  it("ai-critique 선택 시 PostToolUse Hook이 등록된다", () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      workflows: { workflows: ["ai-critique"] },
    };
    const file = generateSettings(options);
    const parsed = JSON.parse(file.content);

    expect(parsed.hooks.PostToolUse.length).toBeGreaterThan(0);
  });
});

describe("generators/scripts", () => {
  it("ralph-loop 선택 시 fix_plan.md를 생성한다", () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      workflows: { workflows: ["ralph-loop"] },
    };
    const files = generateScriptFiles(options);
    const fixPlan = files.find((f) => f.relativePath.includes("fix_plan.md"));
    expect(fixPlan).toBeDefined();
    expect(fixPlan!.content).toContain("작업 큐");
  });

  it("tdd 선택 시 run-tests.sh를 생성한다", () => {
    const files = generateScriptFiles(BASE_OPTIONS);
    const runTests = files.find((f) => f.relativePath.includes("run-tests.sh"));
    expect(runTests).toBeDefined();
    expect(runTests!.content).toContain("pytest");
  });

  it("워크플로우 미선택 시 빈 배열을 반환한다", () => {
    const options: InitOptions = {
      ...BASE_OPTIONS,
      workflows: { workflows: [] },
    };
    const files = generateScriptFiles(options);
    expect(files.length).toBe(0);
  });
});
