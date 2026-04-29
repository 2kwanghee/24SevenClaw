import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { generateAgentFiles } from "../src/generators/agent.js";
import { generateSkillFiles } from "../src/generators/skill.js";
import { generateHookFiles } from "../src/generators/hook.js";
import { generateScriptFiles } from "../src/generators/scripts.js";
import { generateSettings } from "../src/generators/settings.js";
import { generateClaudeMd } from "../src/generators/claude-md.js";
import { writeFiles } from "../src/generators/writer.js";
import type { InitOptions } from "../src/types.js";

const FULL_OPTIONS: InitOptions = {
  project: {
    name: "e2e-project",
    type: "fullstack",
    stack: "fastapi-nextjs",
  },
  agents: {
    agents: ["backend", "frontend", "harness"],
  },
  workflows: {
    workflows: ["tdd", "ai-critique", "linear", "ralph-loop", "harness-gate"],
  },
};

describe("integration — 전체 init 플로우 E2E", () => {
  let tmpDir: string;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "24sc-e2e-"));
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  it("전체 파일 생성 후 올바른 디렉토리 구조를 만든다", async () => {
    const agentFiles = await generateAgentFiles(FULL_OPTIONS);
    const skillFiles = await generateSkillFiles(FULL_OPTIONS);
    const hookFiles = await generateHookFiles(FULL_OPTIONS);
    const scriptFiles = generateScriptFiles(FULL_OPTIONS);
    const settingsFile = generateSettings(FULL_OPTIONS);
    const claudeMdFile = await generateClaudeMd(FULL_OPTIONS);

    const allFiles = [
      ...agentFiles,
      ...skillFiles,
      ...hookFiles,
      ...scriptFiles,
      settingsFile,
      claudeMdFile,
    ];

    const written = await writeFiles(tmpDir, allFiles);

    // 기본 구조 검증
    expect(written.length).toBeGreaterThanOrEqual(10);

    // 디렉토리 존재 확인
    const agentsDir = await fs.stat(path.join(tmpDir, ".claude/agents"));
    expect(agentsDir.isDirectory()).toBe(true);

    const skillsDir = await fs.stat(path.join(tmpDir, ".claude/skills"));
    expect(skillsDir.isDirectory()).toBe(true);

    const scriptsDir = await fs.stat(path.join(tmpDir, "scripts"));
    expect(scriptsDir.isDirectory()).toBe(true);
  });

  it("에이전트 파일이 올바르게 생성된다", async () => {
    const files = await generateAgentFiles(FULL_OPTIONS);
    await writeFiles(tmpDir, files);

    const harness = await fs.readFile(
      path.join(tmpDir, ".claude/agents/harness-guide.md"),
      "utf-8"
    );
    expect(harness).toContain("하네스 엔지니어링");
  });

  it("스킬 파일이 올바르게 생성된다", async () => {
    const files = await generateSkillFiles(FULL_OPTIONS);
    await writeFiles(tmpDir, files);

    const tdd = await fs.readFile(
      path.join(tmpDir, ".claude/skills/tdd-smart-coding.md"),
      "utf-8"
    );
    expect(tdd).toContain("TDD");
    expect(tdd).toContain("pytest");

    const gate = await fs.readFile(
      path.join(tmpDir, ".claude/skills/harness-gate.md"),
      "utf-8"
    );
    expect(gate).toContain("Gate");
  });

  it("Hook 스크립트가 올바르게 생성된다", async () => {
    const files = await generateHookFiles(FULL_OPTIONS);
    await writeFiles(tmpDir, files);

    const gate = await fs.readFile(
      path.join(tmpDir, "scripts/harness-gate.sh"),
      "utf-8"
    );
    expect(gate).toContain("#!/usr/bin/env bash");
    expect(gate).toContain("ruff check");
    expect(gate).toContain("하네스 Gate");
  });

  it("settings.json에 Hook이 올바르게 등록된다", async () => {
    const file = generateSettings(FULL_OPTIONS);
    await writeFiles(tmpDir, [file]);

    const raw = await fs.readFile(
      path.join(tmpDir, ".claude/settings.json"),
      "utf-8"
    );
    const settings = JSON.parse(raw);

    // harness-gate → UserPromptSubmit
    expect(settings.hooks.UserPromptSubmit.length).toBeGreaterThan(0);
    expect(settings.hooks.UserPromptSubmit[0].type).toBe("command");

    // ai-critique → PostToolUse
    expect(settings.hooks.PostToolUse.length).toBeGreaterThan(0);
  });

  it("ralph-loop 선택 시 .ralph/fix_plan.md가 생성된다", async () => {
    const files = generateScriptFiles(FULL_OPTIONS);
    await writeFiles(tmpDir, files);

    const fixPlan = await fs.readFile(
      path.join(tmpDir, ".ralph/fix_plan.md"),
      "utf-8"
    );
    expect(fixPlan).toContain("작업 큐");
    expect(fixPlan).toContain("P0: 긴급");
  });

  it("CLAUDE.md가 올바르게 생성된다", async () => {
    const file = await generateClaudeMd(FULL_OPTIONS);
    await writeFiles(tmpDir, [file]);

    const content = await fs.readFile(
      path.join(tmpDir, "CLAUDE.md"),
      "utf-8"
    );
    expect(content).toContain("e2e-project");
    expect(content).toContain("하네스 엔지니어링");
  });

  it("최소 옵션(워크플로우 없음)에서도 정상 동작한다", async () => {
    const minOptions: InitOptions = {
      project: { name: "min-project", type: "webapp", stack: "fastapi-nextjs" },
      agents: { agents: ["harness"] },
    };

    const agentFiles = await generateAgentFiles(minOptions);
    const skillFiles = await generateSkillFiles(minOptions);
    const hookFiles = await generateHookFiles(minOptions);
    const scriptFiles = generateScriptFiles(minOptions);
    const settingsFile = generateSettings(minOptions);
    const claudeMdFile = await generateClaudeMd(minOptions);

    const allFiles = [
      ...agentFiles,
      ...skillFiles,
      ...hookFiles,
      ...scriptFiles,
      settingsFile,
      claudeMdFile,
    ];

    const written = await writeFiles(tmpDir, allFiles);

    // 최소: harness agent + settings + CLAUDE.md = 3개
    expect(written.length).toBe(3);
    expect(skillFiles.length).toBe(0);
    expect(hookFiles.length).toBe(0);
    expect(scriptFiles.length).toBe(0);
  });
});
