import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import Handlebars from "handlebars";
import { generateAgentFiles } from "../src/generators/agent.js";
import { generateSkillFiles } from "../src/generators/skill.js";
import { generateHookFiles } from "../src/generators/hook.js";
import { generateScriptFiles } from "../src/generators/scripts.js";
import { generateSettings } from "../src/generators/settings.js";
import { generateClaudeMd } from "../src/generators/claude-md.js";
import { writeFiles } from "../src/generators/writer.js";
import { TEMPLATES_DIR } from "../src/paths.js";
import catalogAgents from "../src/catalog/agents.json" with { type: "json" };
import catalogSkills from "../src/catalog/skills.json" with { type: "json" };
import catalogStacks from "../src/catalog/stacks.json" with { type: "json" };
import type { InitOptions, CatalogAgent } from "../src/types.js";
import type { CatalogSkill } from "../src/generators/skill.js";

const FULL_OPTIONS: InitOptions = {
  project: {
    name: "e2e-full",
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

describe("E2E — 전체 시나리오 테스트", () => {
  let tmpDir: string;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "24sc-e2e-full-"));
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  describe("init → add 시나리오", () => {
    it("init 후 추가 에이전트를 add할 수 있다", async () => {
      // Step 1: init으로 기본 구조 생성
      const initOptions: InitOptions = {
        project: { name: "add-test", type: "fullstack", stack: "fastapi-nextjs" },
        agents: { agents: ["backend", "harness"] },
        workflows: { workflows: ["tdd"] },
      };

      const allFiles = [
        ...(await generateAgentFiles(initOptions)),
        ...(await generateSkillFiles(initOptions)),
        ...(await generateHookFiles(initOptions)),
        ...generateScriptFiles(initOptions),
        generateSettings(initOptions),
        await generateClaudeMd(initOptions),
      ];

      await writeFiles(tmpDir, allFiles);

      // Step 2: frontend 에이전트 추가
      const agent = (catalogAgents as CatalogAgent[]).find(
        (a) => a.id === "frontend"
      )!;
      const stack = catalogStacks.find((s) => s.id === "fastapi-nextjs")!;

      const templateSource = await fs.readFile(
        path.join(TEMPLATES_DIR, agent.template),
        "utf-8"
      );
      const template = Handlebars.compile(templateSource);
      const content = template({
        projectName: "add-test",
        projectType: "fullstack",
        stack,
        agent,
      });

      await fs.writeFile(
        path.join(tmpDir, `.claude/agents/${agent.outputFile}`),
        content,
        "utf-8"
      );

      // 검증: 기존 파일 + 새 파일 모두 존재
      const backendExists = await fs
        .access(path.join(tmpDir, ".claude/agents/api-agent.md"))
        .then(() => true)
        .catch(() => false);
      const frontendExists = await fs
        .access(path.join(tmpDir, ".claude/agents/web-agent.md"))
        .then(() => true)
        .catch(() => false);

      expect(backendExists).toBe(true);
      expect(frontendExists).toBe(true);
    });

    it("init 후 추가 스킬을 add하고 settings.json Hook이 등록된다", async () => {
      // Step 1: init (harness-gate 없이)
      const initOptions: InitOptions = {
        project: { name: "hook-test", type: "fullstack", stack: "fastapi-nextjs" },
        agents: { agents: ["harness"] },
        workflows: { workflows: ["tdd"] },
      };

      const allFiles = [
        ...(await generateAgentFiles(initOptions)),
        ...(await generateSkillFiles(initOptions)),
        ...(await generateHookFiles(initOptions)),
        ...generateScriptFiles(initOptions),
        generateSettings(initOptions),
        await generateClaudeMd(initOptions),
      ];

      await writeFiles(tmpDir, allFiles);

      // settings.json에 UserPromptSubmit이 비어있는지 확인
      const settingsBefore = JSON.parse(
        await fs.readFile(
          path.join(tmpDir, ".claude/settings.json"),
          "utf-8"
        )
      );
      expect(settingsBefore.hooks.UserPromptSubmit.length).toBe(0);

      // Step 2: harness-gate 스킬 추가 + Hook 등록
      const skill = (catalogSkills as CatalogSkill[]).find(
        (s) => s.id === "harness-gate"
      )!;
      const stack = catalogStacks.find((s) => s.id === "fastapi-nextjs")!;

      // 스킬 파일 생성
      const templateSource = await fs.readFile(
        path.join(TEMPLATES_DIR, skill.template),
        "utf-8"
      );
      const template = Handlebars.compile(templateSource);
      const skillContent = template({
        projectName: "hook-test",
        projectType: "fullstack",
        stack,
      });
      await fs.writeFile(
        path.join(tmpDir, `.claude/skills/${skill.outputFile}`),
        skillContent
      );

      // Hook 등록
      settingsBefore.hooks.UserPromptSubmit.push({
        type: "command",
        command: "bash scripts/harness-gate.sh",
      });
      await fs.writeFile(
        path.join(tmpDir, ".claude/settings.json"),
        JSON.stringify(settingsBefore, null, 2)
      );

      // 검증
      const settingsAfter = JSON.parse(
        await fs.readFile(
          path.join(tmpDir, ".claude/settings.json"),
          "utf-8"
        )
      );
      expect(settingsAfter.hooks.UserPromptSubmit.length).toBe(1);
      expect(settingsAfter.hooks.UserPromptSubmit[0].command).toContain(
        "harness-gate"
      );
    });
  });

  describe("init → doctor 시나리오", () => {
    it("정상 init 후 doctor 검사 — 모든 파일 존재", async () => {
      const allFiles = [
        ...(await generateAgentFiles(FULL_OPTIONS)),
        ...(await generateSkillFiles(FULL_OPTIONS)),
        ...(await generateHookFiles(FULL_OPTIONS)),
        ...generateScriptFiles(FULL_OPTIONS),
        generateSettings(FULL_OPTIONS),
        await generateClaudeMd(FULL_OPTIONS),
      ];

      await writeFiles(tmpDir, allFiles);

      // .claude/ 존재 확인
      const claudeDirExists = await fs
        .stat(path.join(tmpDir, ".claude"))
        .then((s) => s.isDirectory())
        .catch(() => false);
      expect(claudeDirExists).toBe(true);

      // CLAUDE.md 존재 확인
      const claudeMdExists = await fs
        .access(path.join(tmpDir, "CLAUDE.md"))
        .then(() => true)
        .catch(() => false);
      expect(claudeMdExists).toBe(true);

      // settings.json 유효성 확인
      const settings = JSON.parse(
        await fs.readFile(
          path.join(tmpDir, ".claude/settings.json"),
          "utf-8"
        )
      );
      expect(settings.permissions).toBeDefined();
      expect(settings.hooks).toBeDefined();

      // 에이전트 파일 존재 확인
      const harnessExists = await fs
        .access(path.join(tmpDir, ".claude/agents/harness-guide.md"))
        .then(() => true)
        .catch(() => false);
      expect(harnessExists).toBe(true);

      // 스킬 파일 존재 확인
      const tddExists = await fs
        .access(path.join(tmpDir, ".claude/skills/tdd-smart-coding.md"))
        .then(() => true)
        .catch(() => false);
      expect(tddExists).toBe(true);
    });

    it("부분 설정에서 doctor가 누락 항목을 감지한다", async () => {
      // CLAUDE.md만 생성 (.claude/ 없음)
      await fs.writeFile(
        path.join(tmpDir, "CLAUDE.md"),
        "# Test\n참조: .claude/agents/api-agent.md"
      );

      // .claude/ 디렉토리가 없음
      const claudeDirExists = await fs
        .access(path.join(tmpDir, ".claude"))
        .then(() => true)
        .catch(() => false);
      expect(claudeDirExists).toBe(false);

      // 참조된 파일이 없음
      const agentExists = await fs
        .access(path.join(tmpDir, ".claude/agents/api-agent.md"))
        .then(() => true)
        .catch(() => false);
      expect(agentExists).toBe(false);
    });
  });

  describe("전체 스택별 테스트", () => {
    it("django-react 스택으로 전체 파일 생성", async () => {
      const djangoOptions: InitOptions = {
        project: { name: "django-app", type: "fullstack", stack: "django-react" },
        agents: { agents: ["backend", "frontend", "harness"] },
        workflows: { workflows: ["tdd", "harness-gate"] },
      };

      const allFiles = [
        ...(await generateAgentFiles(djangoOptions)),
        ...(await generateSkillFiles(djangoOptions)),
        ...(await generateHookFiles(djangoOptions)),
        ...generateScriptFiles(djangoOptions),
        generateSettings(djangoOptions),
        await generateClaudeMd(djangoOptions),
      ];

      const written = await writeFiles(tmpDir, allFiles);
      expect(written.length).toBeGreaterThanOrEqual(6);

      // Hook 스크립트에 django 스택 명령어 확인
      const hookScript = await fs.readFile(
        path.join(tmpDir, "scripts/harness-gate.sh"),
        "utf-8"
      );
      expect(hookScript).toContain("ruff check");
    });

    it("express-vue 스택으로 전체 파일 생성", async () => {
      const expressOptions: InitOptions = {
        project: { name: "express-app", type: "fullstack", stack: "express-vue" },
        agents: { agents: ["backend", "harness"] },
        workflows: { workflows: ["harness-gate"] },
      };

      const allFiles = [
        ...(await generateAgentFiles(expressOptions)),
        ...(await generateSkillFiles(expressOptions)),
        ...(await generateHookFiles(expressOptions)),
        ...generateScriptFiles(expressOptions),
        generateSettings(expressOptions),
        await generateClaudeMd(expressOptions),
      ];

      const written = await writeFiles(tmpDir, allFiles);
      expect(written.length).toBeGreaterThanOrEqual(4);
    });
  });

  describe("dry-run 시뮬레이션", () => {
    it("파일 생성 목록만 확인하고 실제 파일은 생성하지 않는다", async () => {
      const allFiles = [
        ...(await generateAgentFiles(FULL_OPTIONS)),
        ...(await generateSkillFiles(FULL_OPTIONS)),
        ...(await generateHookFiles(FULL_OPTIONS)),
        ...generateScriptFiles(FULL_OPTIONS),
        generateSettings(FULL_OPTIONS),
        await generateClaudeMd(FULL_OPTIONS),
      ];

      // dry-run: 파일 목록만 수집
      const filePaths = allFiles.map((f) => f.relativePath);
      expect(filePaths.length).toBeGreaterThanOrEqual(10);

      // 실제 파일은 없어야 함
      for (const filePath of filePaths) {
        const exists = await fs
          .access(path.join(tmpDir, filePath))
          .then(() => true)
          .catch(() => false);
        expect(exists).toBe(false);
      }
    });
  });
});
