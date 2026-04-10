import type { PlatformAdapter, PlatformId } from "./types";
import { ClaudeCodeAdapter } from "./claude-code";
import { GeminiCliAdapter } from "./gemini-cli";

export type { PlatformAdapter, PlatformId };
export { PLATFORM_DIR_MAP } from "./types";

/** 등록된 플랫폼 어댑터 */
const adapters: Record<string, PlatformAdapter> = {
  "claude-code": new ClaudeCodeAdapter(),
  "gemini-cli": new GeminiCliAdapter(),
};

/** 지원하는 플랫폼 목록 */
export function getSupportedPlatforms(): PlatformAdapter[] {
  return Object.values(adapters);
}

/** 플랫폼 ID로 어댑터 조회 (미지원 시 에러) */
export function getPlatformAdapter(platformId: PlatformId): PlatformAdapter {
  const adapter = adapters[platformId];
  if (!adapter) {
    throw new Error(`지원하지 않는 플랫폼: ${platformId}`);
  }
  return adapter;
}
