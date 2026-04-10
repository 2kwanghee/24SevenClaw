import type { InitOptions, CatalogAgent, GeneratedFile } from "../types";
import { loadTemplate } from "../template-loader";
import catalogAgents from "../catalog/agents.json";
import catalogStacks from "../catalog/stacks.json";

/** 선택된 에이전트에 해당하는 .md 파일 생성 */
export async function generateAgentFiles(
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
      relativePath: `.claude/agents/${agent.outputFile}`,
      content,
    });
  }

  return files;
}

/** 에이전트 목록에서 CLAUDE.md에 삽입할 참조 목록 생성 */
export function getAgentReferences(
  options: InitOptions
): { file: string; name: string }[] {
  const selectedAgents = (catalogAgents as CatalogAgent[]).filter(
    (a) => options.agents.agents.includes(a.id) || a.required
  );

  return selectedAgents.map((a) => ({
    file: `.claude/agents/${a.outputFile}`,
    name: a.name,
  }));
}
