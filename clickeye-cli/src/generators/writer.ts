import fs from "node:fs/promises";
import path from "node:path";
import type { GeneratedFile } from "./agent.js";

/** 생성된 파일들을 대상 디렉토리에 기록 */
export async function writeFiles(
  targetDir: string,
  files: GeneratedFile[]
): Promise<string[]> {
  const written: string[] = [];

  for (const file of files) {
    const fullPath = path.join(targetDir, file.relativePath);
    const dir = path.dirname(fullPath);
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(fullPath, file.content, "utf-8");
    written.push(file.relativePath);
  }

  return written;
}
