import type { InitOptions, GeneratedFile } from "../types";

/** .gemini/settings.json 생성 — Gemini CLI 설정 */
export function generateGeminiSettings(options: InitOptions): GeneratedFile {
  const workflows = options.workflows?.workflows ?? [];

  const settings: Record<string, unknown> = {
    coreTools: ["file_edit", "file_read", "shell", "web_search"],
    safetySettings: {
      denyPatterns: [
        "rm -rf *",
        "git push *",
        "git checkout main",
      ],
    },
  };

  if (workflows.includes("harness-gate")) {
    settings.prePromptHook = "bash scripts/harness-gate.sh";
  }

  return {
    relativePath: ".gemini/settings.json",
    content: JSON.stringify(settings, null, 2) + "\n",
  };
}
