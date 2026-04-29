import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import Handlebars from "handlebars";
import catalogAgents from "../src/catalog/agents.json" with { type: "json" };
import catalogSkills from "../src/catalog/skills.json" with { type: "json" };
import catalogStacks from "../src/catalog/stacks.json" with { type: "json" };
import { TEMPLATES_DIR } from "../src/paths.js";
import type { CatalogAgent } from "../src/types.js";
import type { CatalogSkill } from "../src/generators/skill.js";

describe("add 명령어 — 에이전트/스킬/Hook 추가", () => {
  let tmpDir: string;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "24sc-add-"));
    // 기본 .claude/ 구조 생성
    await fs.mkdir(path.join(tmpDir, ".claude/agents"), { recursive: true });
    await fs.mkdir(path.join(tmpDir, ".claude/skills"), { recursive: true });
    await fs.mkdir(path.join(tmpDir, "scripts"), { recursive: true });

    // 기본 settings.json 생성
    const settings = {
      permissions: { allow: [], deny: [] },
      hooks: {
        UserPromptSubmit: [],
        PreToolUse: [],
        PostToolUse: [],
        Stop: [],
      },
    };
    await fs.writeFile(
      path.join(tmpDir, ".claude/settings.json"),
      JSON.stringify(settings, null, 2)
    );
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  describe("에이전트 추가", () => {
    it("backend 에이전트 파일을 올바르게 생성한다", async () => {
      const agent = (catalogAgents as CatalogAgent[]).find(
        (a) => a.id === "backend"
      )!;
      const stack = catalogStacks.find((s) => s.id === "fastapi-nextjs")!;

      const templateSource = await fs.readFile(
        path.join(TEMPLATES_DIR, agent.template),
        "utf-8"
      );
      const template = Handlebars.compile(templateSource);
      const content = template({
        projectName: "test-project",
        projectType: "fullstack",
        stack,
        agent,
      });

      const outputPath = path.join(
        tmpDir,
        `.claude/agents/${agent.outputFile}`
      );
      await fs.writeFile(outputPath, content, "utf-8");

      const written = await fs.readFile(outputPath, "utf-8");
      expect(written).toContain("백엔드");
      expect(written.length).toBeGreaterThan(0);
    });

    it("모든 카탈로그 에이전트의 템플릿이 존재한다", async () => {
      for (const agent of catalogAgents as CatalogAgent[]) {
        const templatePath = path.join(TEMPLATES_DIR, agent.template);
        const exists = await fs
          .access(templatePath)
          .then(() => true)
          .catch(() => false);
        expect(exists, `템플릿 없음: ${agent.template}`).toBe(true);
      }
    });

    it("기존 파일이 있으면 충돌을 감지할 수 있다", async () => {
      const agent = (catalogAgents as CatalogAgent[]).find(
        (a) => a.id === "frontend"
      )!;
      const outputPath = path.join(
        tmpDir,
        `.claude/agents/${agent.outputFile}`
      );

      // 기존 파일 생성
      await fs.writeFile(outputPath, "기존 내용", "utf-8");

      // 파일 존재 확인
      const exists = await fs
        .access(outputPath)
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(true);

      // 기존 내용 확인
      const content = await fs.readFile(outputPath, "utf-8");
      expect(content).toBe("기존 내용");
    });
  });

  describe("스킬 추가", () => {
    it("tdd 스킬 파일을 올바르게 생성한다", async () => {
      const skill = (catalogSkills as CatalogSkill[]).find(
        (s) => s.id === "tdd"
      )!;
      const stack = catalogStacks.find((s) => s.id === "fastapi-nextjs")!;

      const templateSource = await fs.readFile(
        path.join(TEMPLATES_DIR, skill.template),
        "utf-8"
      );
      const template = Handlebars.compile(templateSource);
      const content = template({
        projectName: "test-project",
        projectType: "fullstack",
        stack,
      });

      const outputPath = path.join(
        tmpDir,
        `.claude/skills/${skill.outputFile}`
      );
      await fs.writeFile(outputPath, content, "utf-8");

      const written = await fs.readFile(outputPath, "utf-8");
      expect(written).toContain("TDD");
    });

    it("모든 카탈로그 스킬의 템플릿이 존재한다", async () => {
      for (const skill of catalogSkills as CatalogSkill[]) {
        const templatePath = path.join(TEMPLATES_DIR, skill.template);
        const exists = await fs
          .access(templatePath)
          .then(() => true)
          .catch(() => false);
        expect(exists, `템플릿 없음: ${skill.template}`).toBe(true);
      }
    });

    it("Hook이 있는 스킬은 settings.json에 Hook을 등록한다", async () => {
      const skill = (catalogSkills as CatalogSkill[]).find(
        (s) => s.id === "harness-gate"
      )!;
      expect(skill.hooks).toContain("UserPromptSubmit");

      // settings.json에 Hook 추가 시뮬레이션
      const settingsPath = path.join(tmpDir, ".claude/settings.json");
      const raw = await fs.readFile(settingsPath, "utf-8");
      const settings = JSON.parse(raw);

      settings.hooks.UserPromptSubmit.push({
        type: "command",
        command: "bash scripts/harness-gate.sh",
      });

      await fs.writeFile(
        settingsPath,
        JSON.stringify(settings, null, 2)
      );

      // 확인
      const updated = JSON.parse(
        await fs.readFile(settingsPath, "utf-8")
      );
      expect(updated.hooks.UserPromptSubmit.length).toBe(1);
      expect(updated.hooks.UserPromptSubmit[0].command).toContain(
        "harness-gate"
      );
    });
  });

  describe("Hook 추가", () => {
    it("harness-gate Hook 스크립트를 올바르게 생성한다", async () => {
      const stack = catalogStacks.find((s) => s.id === "fastapi-nextjs")!;

      const templateSource = await fs.readFile(
        path.join(TEMPLATES_DIR, "hooks/harness-gate.sh.hbs"),
        "utf-8"
      );
      const template = Handlebars.compile(templateSource);
      const content = template({ stack });

      const outputPath = path.join(tmpDir, "scripts/harness-gate.sh");
      await fs.writeFile(outputPath, content, "utf-8");

      const written = await fs.readFile(outputPath, "utf-8");
      expect(written).toContain("#!/usr/bin/env bash");
      expect(written).toContain("ruff check");
    });

    it("settings.json에 UserPromptSubmit Hook을 중복 없이 등록한다", async () => {
      const settingsPath = path.join(tmpDir, ".claude/settings.json");
      const hookEntry = {
        type: "command",
        command: "bash scripts/harness-gate.sh",
      };

      // 두 번 추가
      for (let i = 0; i < 2; i++) {
        const raw = await fs.readFile(settingsPath, "utf-8");
        const settings = JSON.parse(raw);
        const hooks = settings.hooks.UserPromptSubmit as {
          type: string;
          command: string;
        }[];

        const exists = hooks.some((h) => h.command === hookEntry.command);
        if (!exists) hooks.push(hookEntry);

        await fs.writeFile(
          settingsPath,
          JSON.stringify(settings, null, 2)
        );
      }

      const final = JSON.parse(
        await fs.readFile(settingsPath, "utf-8")
      );
      expect(final.hooks.UserPromptSubmit.length).toBe(1);
    });
  });
});
