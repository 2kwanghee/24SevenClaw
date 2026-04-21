import type { InitOptions, GeneratedFile } from "../types";
import { loadTemplate } from "../template-loader";
import catalogStacks from "../catalog/stacks.json";

/** harness-gate.sh Hook 스크립트 생성 */
export async function generateHookFiles(
  options: InitOptions
): Promise<GeneratedFile[]> {
  const workflows = options.workflows?.workflows ?? [];

  if (!workflows.includes("harness-gate")) return [];

  const stack = catalogStacks.find((s) => s.id === options.project.stack);
  const template = await loadTemplate("hooks/harness-gate.sh.hbs");
  const content = template({ stack });

  return [
    {
      relativePath: "scripts/harness-gate.sh",
      content,
    },
  ];
}
