import type { InitOptions, GeneratedFile } from "../types";

/** 지원 플랫폼 ID */
export type PlatformId = "claude-code" | "gemini-cli" | "cursor" | "codex";

/** 플랫폼 어댑터 인터페이스 — 각 AI 개발 플랫폼의 파일 생성 규칙을 정의 */
export interface PlatformAdapter {
  readonly id: PlatformId;
  readonly name: string;
  readonly description: string;

  /** 설정 디렉토리 경로 (예: .claude, .gemini, .cursor) */
  getConfigDir(): string;

  /** 에이전트 파일 디렉토리 (예: .claude/agents) */
  getAgentDir(): string;

  /** 설정 파일 경로 (예: .claude/settings.json) */
  getSettingsFile(): string;

  /** 루트 가이드 파일 경로 (예: CLAUDE.md, GEMINI.md) */
  getRootGuideFile(): string;

  /** 플랫폼별 파일 생성 */
  generateFiles(options: InitOptions): Promise<GeneratedFile[]>;
}

/** 플랫폼별 디렉토리 매핑 정의 */
export const PLATFORM_DIR_MAP: Record<
  PlatformId,
  {
    configDir: string;
    agentDir: string;
    settingsFile: string;
    rootGuide: string;
  }
> = {
  "claude-code": {
    configDir: ".claude",
    agentDir: ".claude/agents",
    settingsFile: ".claude/settings.json",
    rootGuide: "CLAUDE.md",
  },
  "gemini-cli": {
    configDir: ".gemini",
    agentDir: ".gemini/agents",
    settingsFile: ".gemini/settings.json",
    rootGuide: "GEMINI.md",
  },
  cursor: {
    configDir: ".cursor",
    agentDir: ".cursor/rules",
    settingsFile: ".cursor/settings.json",
    rootGuide: ".cursorrules",
  },
  codex: {
    configDir: ".codex",
    agentDir: ".codex/agents",
    settingsFile: ".codex/settings.json",
    rootGuide: "CODEX.md",
  },
};
