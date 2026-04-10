import type { InitOptions, CatalogAgent, GeneratedFile } from "../types";
import { loadTemplate } from "../template-loader";
import catalogAgents from "../catalog/agents.json";
import catalogStacks from "../catalog/stacks.json";

/** GEMINI.md 생성 — 프로젝트 루트 가이드 */
export async function generateGeminiMd(
  options: InitOptions
): Promise<GeneratedFile> {
  const template = await loadTemplate("gemini.md.hbs");

  const stack = catalogStacks.find((s) => s.id === options.project.stack);
  const selectedAgents = (catalogAgents as CatalogAgent[]).filter(
    (a) => options.agents.agents.includes(a.id) || a.required
  );
  const agentRefs = selectedAgents.map((a) => ({
    file: `.gemini/agents/${a.outputFile}`,
    name: a.name,
  }));

  const content = template({
    projectName: options.project.name,
    projectType: options.project.type,
    stack,
    agentRefs,
    generatedAt: new Date().toISOString().split("T")[0],
  });

  return {
    relativePath: "GEMINI.md",
    content,
  };
}
