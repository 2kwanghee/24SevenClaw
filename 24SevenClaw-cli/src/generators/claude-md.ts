import fs from "node:fs/promises";
import Handlebars from "handlebars";
import type { InitOptions } from "../types.js";
import type { GeneratedFile } from "./agent.js";
import { getAgentReferences } from "./agent.js";
import catalogStacks from "../catalog/stacks.json" with { type: "json" };

const TEMPLATES_DIR = new URL("../templates/", import.meta.url);

/** CLAUDE.md 생성 — 프로젝트 루트 가이드 */
export async function generateClaudeMd(
  options: InitOptions
): Promise<GeneratedFile> {
  const templateSource = await fs.readFile(
    new URL("claude.md.hbs", TEMPLATES_DIR),
    "utf-8"
  );
  const template = Handlebars.compile(templateSource);

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
