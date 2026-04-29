import type { InitOptions, GeneratedFile } from "../types";
import { loadTemplate } from "../template-loader";
import { getAgentReferences } from "./agent";
import catalogStacks from "../catalog/stacks.json";

/** CLAUDE.md 생성 — 프로젝트 루트 가이드 */
export async function generateClaudeMd(
  options: InitOptions
): Promise<GeneratedFile> {
  const template = await loadTemplate("claude.md.hbs");

  const stack = catalogStacks.find((s) => s.id === options.project.stack);
  const agentRefs = getAgentReferences(options);

  const content = template({
    projectName: options.project.name,
    projectType: options.project.type,
    stack,
    agentRefs,
    generatedAt: new Date().toISOString().split("T")[0],
  });

  return {
    relativePath: "CLAUDE.md",
    content,
  };
}
