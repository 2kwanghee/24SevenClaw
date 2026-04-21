import type { InitOptions, CatalogAgent, CatalogSkill, GeneratedFile } from "../types";
import type { PlatformAdapter } from "./types";
import { PLATFORM_DIR_MAP } from "./types";
import { loadTemplate } from "../template-loader";
import catalogAgents from "../catalog/agents.json";
import catalogSkills from "../catalog/skills.json";
import catalogStacks from "../catalog/stacks.json";
import { generateGeminiMd } from "../generators/gemini-md";
import { generateGeminiSettings } from "../generators/gemini-settings";

const dirs = PLATFORM_DIR_MAP["gemini-cli"];

/**
 * Gemini CLI 플랫폼 어댑터
 *
 * .gemini/ 디렉토리 구조:
 *   .gemini/
 *   ├-- agents/          # 에이전트 가이드 (.md)
 *   ├-- skills/          # 스킬/워크플로우 (.md)
 *   └-- settings.json    # Gemini CLI 설정
 *   GEMINI.md            # 루트 프로젝트 가이드
 */
export class GeminiCliAdapter implements PlatformAdapter {
  readonly id = "gemini-cli" as const;
  readonly name = "Gemini CLI";
  readonly description =
    "Google Gemini CLI — .gemini/ 기반 AI 에이전트 개발 환경";

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
    const [agentFiles, skillFiles, geminiMd] = await Promise.all([
      this.generateAgentFiles(options),
      this.generateSkillFiles(options),
      generateGeminiMd(options),
    ]);

    const files: GeneratedFile[] = [];
    files.push(...agentFiles);
    files.push(...skillFiles);
    files.push(geminiMd);

    // 동기 생성기
    files.push(generateGeminiSettings(options));

    return files;
  }

  /** 에이전트 .md 파일을 .gemini/agents/ 하위에 생성 (기존 템플릿 재활용) */
  private async generateAgentFiles(
    options: InitOptions
  ): Promise<GeneratedFile[]> {
    const stack = catalogStacks.find((s) => s.id === options.project.stack);
    const selectedAgents = (catalogAgents as CatalogAgent[]).filter(
      (a) => options.agents.agents.includes(a.id) || a.required
    );

    const files: GeneratedFile[] = [];

    for (const agent of selectedAgents) {
      const template = await loadTemplate(agent.template);
      const content = template({
        projectName: options.project.name,
        projectType: options.project.type,
        stack,
        agent,
      });

      files.push({
        relativePath: `${dirs.agentDir}/${agent.outputFile}`,
        content,
      });
    }

    return files;
  }

  /** 스킬 .md 파일을 .gemini/skills/ 하위에 생성 (기존 템플릿 재활용) */
  private async generateSkillFiles(
    options: InitOptions
  ): Promise<GeneratedFile[]> {
    const workflows = options.workflows?.workflows ?? [];
    if (workflows.length === 0) return [];

    const stack = catalogStacks.find((s) => s.id === options.project.stack);
    const selectedSkills = (catalogSkills as CatalogSkill[]).filter((s) =>
      (workflows as string[]).includes(s.id)
    );

    const files: GeneratedFile[] = [];

    for (const skill of selectedSkills) {
      const template = await loadTemplate(skill.template);
      const content = template({
        projectName: options.project.name,
        projectType: options.project.type,
        stack,
      });

      files.push({
        relativePath: `.gemini/skills/${skill.outputFile}`,
        content,
      });
    }

    return files;
  }
}
