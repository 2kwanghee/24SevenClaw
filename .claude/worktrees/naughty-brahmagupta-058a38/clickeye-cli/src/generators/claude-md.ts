import fs from "node:fs/promises";
import path from "node:path";
import Handlebars from "handlebars";
import type { InitOptions } from "../types.js";
import type { GeneratedFile } from "./agent.js";
import { getAgentReferences } from "./agent.js";
import catalogStacks from "../catalog/stacks.json" with { type: "json" };
import { TEMPLATES_DIR } from "../paths.js";

/** CLAUDE.md 생성 — 프로젝트 루트 가이드 */
export async function generateClaudeMd(
  options: InitOptions
): Promise<GeneratedFile> {
  const templateSource = await fs.readFile(
    path.join(TEMPLATES_DIR, "claude.md.hbs"),
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
