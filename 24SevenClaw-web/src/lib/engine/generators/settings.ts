import type { InitOptions, GeneratedFile } from "../types";
import { getSelectedSkills } from "./skill";

interface HookEntry {
  type: "command";
  command: string;
}

interface SettingsHooks {
  UserPromptSubmit: HookEntry[];
  PreToolUse: HookEntry[];
  PostToolUse: HookEntry[];
  Stop: HookEntry[];
}

/** settings.json 생성 — Claude Code 권한 + Hook 설정 */
export function generateSettings(options: InitOptions): GeneratedFile {
  const hooks: SettingsHooks = {
    UserPromptSubmit: [],
    PreToolUse: [],
    PostToolUse: [],
    Stop: [],
  };

  const workflows = options.workflows?.workflows ?? [];

  if (workflows.includes("harness-gate")) {
    hooks.UserPromptSubmit.push({
      type: "command",
      command: "bash scripts/harness-gate.sh",
    });
  }

  const selectedSkills = getSelectedSkills(options);
  for (const skill of selectedSkills) {
    for (const hookName of skill.hooks) {
      if (hookName === "PostToolUse") {
        hooks.PostToolUse.push({
          type: "command",
          command: `echo "🔍 AI 리뷰: ${skill.name} 검증 중..."`,
        });
      }
    }
  }

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
    hooks,
  };

  return {
    relativePath: ".claude/settings.json",
    content: JSON.stringify(settings, null, 2) + "\n",
  };
}
