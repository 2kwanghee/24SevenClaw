import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function resolveDir(name: string): string {
  // 번들 모드: dist/{name}/
  const bundled = path.join(__dirname, name);
  if (fs.existsSync(bundled)) return bundled;

  // 소스 모드 (vitest): src/generators/ → src/{name}/
  const source = path.join(__dirname, "..", name);
  if (fs.existsSync(source)) return source;

  throw new Error(`${name} 디렉토리를 찾을 수 없습니다`);
}

export const TEMPLATES_DIR = resolveDir("templates");
export const CATALOG_DIR = resolveDir("catalog");
