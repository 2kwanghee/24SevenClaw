import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import { generateAgentFiles, getAgentReferences } from "../src/generators/agent.js";
import { generateSettings } from "../src/generators/settings.js";
import { generateClaudeMd } from "../src/generators/claude-md.js";
import { writeFiles } from "../src/generators/writer.js";
import type { InitOptions } from "../src/types.js";

const TEST_OPTIONS: InitOptions = {
  project: {
    name: "test-project",
    type: "fullstack",
    stack: "fastapi-nextjs",
  },
  agents: {
    agents: ["backend", "frontend", "harness"],
  },
};

describe("generators/agent", () => {
  it("선택된 에이전트에 맞는 파일을 생성한다", async () => {
    const files = await generateAgentFiles(TEST_OPTIONS);

    // backend + frontend + harness (필수) = 3개
    expect(files.length).toBe(3);

    const paths = files.map((f) => f.relativePath);
    expect(paths).toContain(".claude/agents/api-agent.md");
    expect(paths).toContain(".claude/agents/web-agent.md");
    expect(paths).toContain(".claude/agents/harness-guide.md");
  });

  it("생성된 에이전트 파일에 프로젝트 이름이 포함된다 (하네스 제외)", async () => {
    const files = await generateAgentFiles(TEST_OPTIONS);
    const nonHarnessFiles = files.filter(
      (f) => !f.relativePath.includes("harness-guide")
    );

    for (const file of nonHarnessFiles) {
      expect(file.content).toContain("test-project");
    }
  });

  it("하네스 에이전트는 항상 포함된다", async () => {
    const minimalOptions: InitOptions = {
      project: { name: "min-project", type: "webapp", stack: "fastapi-nextjs" },
      agents: { agents: ["harness"] },
    };

    const files = await generateAgentFiles(minimalOptions);
    const paths = files.map((f) => f.relativePath);
    expect(paths).toContain(".claude/agents/harness-guide.md");
  });

  it("getAgentReferences는 올바른 참조 목록을 반환한다", () => {
    const refs = getAgentReferences(TEST_OPTIONS);
    expect(refs.length).toBe(3);
    expect(refs.some((r) => r.file.includes("harness-guide.md"))).toBe(true);
  });
});

describe("generators/settings", () => {
  it("유효한 JSON settings.json을 생성한다", () => {
    const file = generateSettings(TEST_OPTIONS);
    expect(file.relativePath).toBe(".claude/settings.json");

    const parsed = JSON.parse(file.content);
    expect(parsed).toHaveProperty("permissions");
    expect(parsed).toHaveProperty("hooks");
    expect(parsed.permissions).toHaveProperty("allow");
    expect(parsed.permissions).toHaveProperty("deny");
  });
});

describe("generators/claude-md", () => {
  it("CLAUDE.md를 생성한다", async () => {
    const file = await generateClaudeMd(TEST_OPTIONS);
    expect(file.relativePath).toBe("CLAUDE.md");
    expect(file.content).toContain("test-project");
    expect(file.content).toContain("하네스 엔지니어링");
  });

  it("스택 정보가 포함된다", async () => {
    const file = await generateClaudeMd(TEST_OPTIONS);
    expect(file.content).toContain("FastAPI");
  });

  it("에이전트 참조가 포함된다", async () => {
    const file = await generateClaudeMd(TEST_OPTIONS);
    expect(file.content).toContain("api-agent.md");
    expect(file.content).toContain("harness-guide.md");
  });
});

describe("generators/writer", () => {
  let tmpDir: string;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "24sc-test-"));
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  it("파일을 올바른 경로에 기록한다", async () => {
    const files = [
      { relativePath: ".claude/agents/test.md", content: "# Test" },
      { relativePath: "CLAUDE.md", content: "# Root" },
    ];

    const written = await writeFiles(tmpDir, files);
    expect(written.length).toBe(2);

    const testContent = await fs.readFile(
      path.join(tmpDir, ".claude/agents/test.md"),
      "utf-8"
    );
    expect(testContent).toBe("# Test");
  });

  it("중첩 디렉토리를 자동 생성한다", async () => {
    const files = [
      { relativePath: "deep/nested/dir/file.md", content: "content" },
    ];

    await writeFiles(tmpDir, files);

    const stat = await fs.stat(path.join(tmpDir, "deep/nested/dir/file.md"));
    expect(stat.isFile()).toBe(true);
  });
});
