import "server-only";
import fs from "node:fs/promises";
import path from "node:path";
import Handlebars from "handlebars";

const TEMPLATES_DIR = path.join(
  process.cwd(),
  "src/lib/engine/templates"
);

const templateCache = new Map<string, HandlebarsTemplateDelegate>();

/** 템플릿 파일을 로드하고 컴파일 (캐시 적용) */
export async function loadTemplate(
  templatePath: string
): Promise<HandlebarsTemplateDelegate> {
  const cached = templateCache.get(templatePath);
  if (cached) return cached;

  const fullPath = path.join(TEMPLATES_DIR, templatePath);
  const source = await fs.readFile(fullPath, "utf-8");
  const compiled = Handlebars.compile(source);
  templateCache.set(templatePath, compiled);
  return compiled;
}
