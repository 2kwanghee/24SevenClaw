import type { InitOptions, GeneratedFile } from "../types";
import type { PlatformAdapter } from "./types";
import { PLATFORM_DIR_MAP } from "./types";
import { generateAgentFiles } from "../generators/agent";
import { generateSkillFiles } from "../generators/skill";
import { generateSettings } from "../generators/settings";
import { generateClaudeMd } from "../generators/claude-md";

const dirs = PLATFORM_DIR_MAP["claude-code"];

/**
 * Claude Code 플랫폼 어댑터
 *
 * .claude/ 디렉토리 구조:
 *   .claude/
 *   ├-- agents/          # 에이전트 가이드 (.md)
 *   ├-- skills/          # 스킬/워크플로우 (.md)
 *   └-- settings.json    # 권한 + Hook 설정
 *   CLAUDE.md            # 루트 프로젝트 가이드
 */
export class ClaudeCodeAdapter implements PlatformAdapter {
  readonly id = "claude-code" as const;
  readonly name = "Claude Code";
  readonly description =
    "Anthropic Claude Code — .claude/ 기반 AI 에이전트 개발 환경";

  getConfigDir(): string {
    return dirs.configDir;
  }

  getAgentDir(): string {
    return dirs.agentDir;
  }

  getSettingsFile(): string {
    return dirs.settingsFile;
  }

  getRootGuideFile(): string {
    return dirs.rootGuide;
  }

  async generateFiles(options: InitOptions): Promise<GeneratedFile[]> {
    // 비동기 생성기 병렬 실행
    const [agentFiles, skillFiles, claudeMd] = await Promise.all([
      generateAgentFiles(options),
      generateSkillFiles(options),
      generateClaudeMd(options),
    ]);

    const files: GeneratedFile[] = [];
    files.push(...agentFiles);
    files.push(...skillFiles);
    files.push(claudeMd);

    // 동기 생성기
    files.push(generateSettings(options));

    return files;
  }
}
