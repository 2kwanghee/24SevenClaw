import fs from "node:fs/promises";
import path from "node:path";
import Handlebars from "handlebars";
import type { InitOptions } from "../types.js";
import type { GeneratedFile } from "./agent.js";
import catalogStacks from "../catalog/stacks.json" with { type: "json" };
import { TEMPLATES_DIR } from "../paths.js";

/** harness-gate.sh Hook 스크립트 생성 */
export async function generateHookFiles(
  options: InitOptions
): Promise<GeneratedFile[]> {
  const workflows = options.workflows?.workflows ?? [];

  // harness-gate가 선택되었을 때만 Hook 파일 생성
  if (!workflows.includes("harness-gate")) return [];

  const stack = catalogStacks.find((s) => s.id === options.project.stack);

  const templateSource = await fs.readFile(
    path.join(TEMPLATES_DIR, "hooks/harness-gate.sh.hbs"),
    "utf-8"
  );
  const template = Handlebars.compile(templateSource);
  const content = template({ stack });

  return [
    {
      relativePath: "scripts/harness-gate.sh",
      content,
    },
  ];
}
