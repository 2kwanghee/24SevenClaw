import type { InitOptions, CatalogSkill, GeneratedFile } from "../types";
import { loadTemplate } from "../template-loader";
import catalogSkills from "../catalog/skills.json";
import catalogStacks from "../catalog/stacks.json";

/** 선택된 워크플로우에 해당하는 스킬 .md 파일 생성 */
export async function generateSkillFiles(
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
    (workflows as string[]).includes(s.id)
  );
}
