"use client";

import { Terminal, Zap, Code2, Cpu } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

const PLATFORM_OPTIONS = [
  {
    id: "claude-code",
    label: "Claude Code",
    description: "Anthropic Claude 기반 AI 코딩 에이전트",
    icon: Terminal,
    recommended: true,
  },
  {
    id: "gemini-cli",
    label: "Gemini CLI",
    description: "Google Gemini 기반 CLI 에이전트",
    icon: Zap,
    recommended: false,
  },
  {
    id: "cursor",
    label: "Cursor",
    description: "AI-first 코드 에디터",
    icon: Code2,
    recommended: false,
  },
  {
    id: "codex",
    label: "Codex",
    description: "OpenAI Codex 기반 에이전트",
    icon: Cpu,
    recommended: false,
  },
] as const;

export function StepSolutionPlatform() {
  const platformId = useSolutionWizardStore((s) => s.data.platform.platformId);
  const setPlatform = useSolutionWizardStore((s) => s.setPlatform);

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400">
        생성된 솔루션을 실행할 Agent 플랫폼을 선택하세요.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {PLATFORM_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const isSelected = platformId === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => setPlatform({ platformId: opt.id })}
              aria-pressed={isSelected}
              className={`relative flex items-start gap-3 rounded-xl border p-4 text-left transition-all duration-200 ${
                isSelected
                  ? "border-emerald-500/50 bg-emerald-500/10 ring-2 ring-emerald-500/20"
                  : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
              }`}
            >
              {opt.recommended && (
                <span className="absolute right-3 top-3 rounded-md bg-emerald-500/20 px-1.5 py-0.5 text-xs font-medium text-emerald-300">
                  추천
                </span>
              )}
              <Icon
                className={`mt-0.5 h-5 w-5 shrink-0 ${isSelected ? "text-emerald-400" : "text-slate-400"}`}
              />
              <div>
                <p
                  className={`text-sm font-semibold ${isSelected ? "text-white" : "text-slate-300"}`}
                >
                  {opt.label}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {opt.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
