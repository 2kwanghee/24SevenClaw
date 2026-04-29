import "server-only";
import type { InitOptions, GeneratedFile } from "./types";
import { getPlatformAdapter } from "./platforms";
import { generateEnvFiles } from "./generators/env";
import { generateHookFiles } from "./generators/hook";
import { generateScriptFiles } from "./generators/scripts";

export type { InitOptions, GeneratedFile };
export type {
  ProjectType,
  StackPreset,
  AgentId,
  WorkflowId,
  ProjectInfo,
  AgentSelection,
  WorkflowSelection,
  CatalogAgent,
  CatalogSkill,
  CatalogStack,
  EnvVarDefinition,
} from "./types";
export type { PlatformId, PlatformAdapter } from "./platforms";
export { getPlatformAdapter, getSupportedPlatforms, PLATFORM_DIR_MAP } from "./platforms";

/**
 * 모든 생성기를 실행하고 결과를 Map<relativePath, content>로 반환.
 * 플랫폼 어댑터가 플랫폼별 파일을 생성하고,
 * 공통 파일(스크립트, 훅)은 별도로 생성한다.
 */
export async function generateAll(
  options: InitOptions
): Promise<Map<string, string>> {
  const adapter = getPlatformAdapter(options.platformId ?? "claude-code");

  // 플랫폼별 파일 + 공통 파일 병렬 생성
  const [platformFiles, hookFiles] = await Promise.all([
    adapter.generateFiles(options),
    generateHookFiles(options),
  ]);

  // 동기 생성기
  const scriptFiles = generateScriptFiles(options);
  const envFiles = generateEnvFiles(options);

  // Map 변환: relativePath → content
  const result = new Map<string, string>();
  const allFiles: GeneratedFile[] = [
    ...platformFiles,
    ...hookFiles,
    ...scriptFiles,
    ...envFiles,
  ];

  for (const file of allFiles) {
    result.set(file.relativePath, file.content);
  }

  return result;
}
