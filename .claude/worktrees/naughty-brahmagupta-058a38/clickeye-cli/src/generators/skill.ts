import fs from "node:fs/promises";
import path from "node:path";
import Handlebars from "handlebars";
import type { InitOptions } from "../types.js";
import type { GeneratedFile } from "./agent.js";
import catalogSkills from "../catalog/skills.json" with { type: "json" };
import catalogStacks from "../catalog/stacks.json" with { type: "json" };
import { TEMPLATES_DIR } from "../paths.js";

export interface CatalogSkill {
  id: string;
  name: string;
  description: string;
  template: string;
  outputFile: string;
  dependencies: string[];
  hooks: string[];
}

/** 선택된 워크플로우에 해당하는 스킬 .md 파일 생성 */
export async function generateSkillFiles(
  options: InitOptions
): Promise<GeneratedFile[]> {
  const workflows = options.workflows?.workflows ?? [];
  if (workflows.length === 0) return [];

  const stack = catalogStacks.find((s) => s.id === options.project.stack);
  const selectedSkills = (catalogSkills as CatalogSkill[]).filter((s) =>
    workflows.includes(s.id as typeof workflows[number])
  );

  const files: GeneratedFile[] = [];

  for (const skill of selectedSkills) {
    const templateSource = await fs.readFile(
      path.join(TEMPLATES_DIR, skill.template),
      "utf-8"
    );
    const template = Handlebars.compile(templateSource);
    const content = template({
      projectName: options.project.name,
      projectType: options.project.type,
      stack,
    });

    files.push({
      relativePath: `.claude/skills/${skill.outputFile}`,
      content,
    });
  }

  return files;
}

/** 선택된 스킬 목록 반환 */
export function getSelectedSkills(options: InitOptions): CatalogSkill[] {
  const workflows = options.workflows?.workflows ?? [];
  return (catalogSkills as CatalogSkill[]).filter((s) =>
    workflows.includes(s.id as typeof workflows[number])
  );
}
