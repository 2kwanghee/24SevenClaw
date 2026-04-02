import type { InitOptions } from "../types.js";
import type { GeneratedFile } from "./agent.js";

/** settings.json 생성 — Claude Code 권한 + Hook 설정 */
export function generateSettings(options: InitOptions): GeneratedFile {
  const settings: Record<string, unknown> = {
    permissions: {
      allow: [
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash(npm run lint:*)",
        "Bash(npm run test:*)",
        "Bash(npx tsc --noEmit)",
      ],
      deny: [
        "Bash(rm -rf *)",
        "Bash(git push *)",
        "Bash(git checkout main)",
      ],
    },
    hooks: {
      UserPromptSubmit: [],
      PreToolUse: [],
      PostToolUse: [],
      Stop: [],
    },
  };

  return {
    relativePath: ".claude/settings.json",
    content: JSON.stringify(settings, null, 2) + "\n",
  };
}
