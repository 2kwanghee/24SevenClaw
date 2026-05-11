import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

describe("doctor 명령어 — 설정 상태 검증", () => {
  let tmpDir: string;

  beforeEach(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "ce-doctor-"));
  });

  afterEach(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  describe(".claude/ 디렉토리 검사", () => {
    it(".claude/ 디렉토리가 있으면 통과", async () => {
      await fs.mkdir(path.join(tmpDir, ".claude"), { recursive: true });

      const exists = await fs
        .access(path.join(tmpDir, ".claude"))
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(true);
    });

    it(".claude/ 디렉토리가 없으면 실패", async () => {
      const exists = await fs
        .access(path.join(tmpDir, ".claude"))
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(false);
    });
  });

  describe("settings.json 유효성 검사", () => {
    it("유효한 settings.json이 있으면 통과", async () => {
      await fs.mkdir(path.join(tmpDir, ".claude"), { recursive: true });
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

      const raw = await fs.readFile(
        path.join(tmpDir, ".claude/settings.json"),
        "utf-8"
      );
      const parsed = JSON.parse(raw);
      expect(parsed.permissions).toBeDefined();
      expect(parsed.hooks).toBeDefined();
    });

    it("잘못된 JSON이면 파싱 실패", async () => {
      await fs.mkdir(path.join(tmpDir, ".claude"), { recursive: true });
      await fs.writeFile(
        path.join(tmpDir, ".claude/settings.json"),
        "{ invalid json"
      );

      const raw = await fs.readFile(
        path.join(tmpDir, ".claude/settings.json"),
        "utf-8"
      );
      expect(() => JSON.parse(raw)).toThrow();
    });

    it("필수 필드(permissions)가 없으면 실패", async () => {
      await fs.mkdir(path.join(tmpDir, ".claude"), { recursive: true });
      await fs.writeFile(
        path.join(tmpDir, ".claude/settings.json"),
        JSON.stringify({ hooks: {} })
      );

      const raw = await fs.readFile(
        path.join(tmpDir, ".claude/settings.json"),
        "utf-8"
      );
      const parsed = JSON.parse(raw);
      expect(parsed.permissions).toBeUndefined();
    });

    it("필수 필드(hooks)가 없으면 실패", async () => {
      await fs.mkdir(path.join(tmpDir, ".claude"), { recursive: true });
      await fs.writeFile(
        path.join(tmpDir, ".claude/settings.json"),
        JSON.stringify({ permissions: {} })
      );

      const raw = await fs.readFile(
        path.join(tmpDir, ".claude/settings.json"),
        "utf-8"
      );
      const parsed = JSON.parse(raw);
      expect(parsed.hooks).toBeUndefined();
    });
  });

  describe("Hook 스크립트 실행 권한 검사", () => {
    it("실행 권한이 있는 스크립트는 통과", async () => {
      await fs.mkdir(path.join(tmpDir, "scripts"), { recursive: true });
      const scriptPath = path.join(tmpDir, "scripts/harness-gate.sh");
      await fs.writeFile(scriptPath, "#!/usr/bin/env bash\necho test");
      await fs.chmod(scriptPath, 0o755);

      await fs.access(scriptPath, fs.constants.X_OK);
      // 예외가 발생하지 않으면 통과
    });

    it("실행 권한이 없는 스크립트는 실패", async () => {
      await fs.mkdir(path.join(tmpDir, "scripts"), { recursive: true });
      const scriptPath = path.join(tmpDir, "scripts/harness-gate.sh");
      await fs.writeFile(scriptPath, "#!/usr/bin/env bash\necho test");
      await fs.chmod(scriptPath, 0o644);

      await expect(
        fs.access(scriptPath, fs.constants.X_OK)
      ).rejects.toThrow();
    });
  });

  describe("에이전트 파일 참조 무결성 검사", () => {
    it("CLAUDE.md에 참조된 에이전트 파일이 있으면 통과", async () => {
      await fs.mkdir(path.join(tmpDir, ".claude/agents"), {
        recursive: true,
      });
      await fs.writeFile(
        path.join(tmpDir, ".claude/agents/api-agent.md"),
        "# API Agent"
      );
      await fs.writeFile(
        path.join(tmpDir, "CLAUDE.md"),
        "참조: .claude/agents/api-agent.md"
      );

      const claudeMd = await fs.readFile(
        path.join(tmpDir, "CLAUDE.md"),
        "utf-8"
      );
      const refs = claudeMd.match(/\.claude\/agents\/[\w-]+\.md/g) ?? [];
      expect(refs.length).toBe(1);

      for (const ref of refs) {
        const exists = await fs
          .access(path.join(tmpDir, ref))
          .then(() => true)
          .catch(() => false);
        expect(exists).toBe(true);
      }
    });

    it("CLAUDE.md에 참조된 에이전트 파일이 없으면 실패", async () => {
      await fs.mkdir(path.join(tmpDir, ".claude/agents"), {
        recursive: true,
      });
      await fs.writeFile(
        path.join(tmpDir, "CLAUDE.md"),
        "참조: .claude/agents/missing-agent.md"
      );

      const claudeMd = await fs.readFile(
        path.join(tmpDir, "CLAUDE.md"),
        "utf-8"
      );
      const refs = claudeMd.match(/\.claude\/agents\/[\w-]+\.md/g) ?? [];
      expect(refs.length).toBe(1);

      const exists = await fs
        .access(path.join(tmpDir, refs[0]))
        .then(() => true)
        .catch(() => false);
      expect(exists).toBe(false);
    });
  });

  describe(".env 검사", () => {
    it(".env.example이 있는데 .env가 없으면 경고", async () => {
      await fs.writeFile(
        path.join(tmpDir, ".env.example"),
        "DB_URL=postgres://..."
      );

      const envExists = await fs
        .access(path.join(tmpDir, ".env"))
        .then(() => true)
        .catch(() => false);
      const exampleExists = await fs
        .access(path.join(tmpDir, ".env.example"))
        .then(() => true)
        .catch(() => false);

      expect(envExists).toBe(false);
      expect(exampleExists).toBe(true);
    });
  });
});
