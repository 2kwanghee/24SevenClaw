"use client";

import { useEffect } from "react";
import { Terminal, Zap, Code2, Cpu } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

const PLATFORM_OPTIONS = [
  {
    id: "claude-code",
    label: "Claude Code",
    description: "Anthropic Claude 기반 AI 코딩 에이전트",
    icon: Terminal,
    badge: "추천",
    available: true,
  },
  {
    id: "gemini-cli",
    label: "Gemini CLI",
    description: "Google Gemini 기반 CLI 에이전트",
    icon: Zap,
    badge: "Coming soon",
    available: false,
  },
  {
    id: "cursor",
    label: "Cursor",
    description: "AI-first 코드 에디터",
    icon: Code2,
    badge: "Coming soon",
    available: false,
  },
  {
    id: "codex",
    label: "Codex",
    description: "OpenAI Codex 기반 에이전트",
    icon: Cpu,
    badge: "Coming soon",
    available: false,
  },
] as const;

export function StepSolutionPlatform() {
  const platformId = useSolutionWizardStore((s) => s.data.platform.platformId);
  const setPlatform = useSolutionWizardStore((s) => s.setPlatform);

  useEffect(() => {
    if (!platformId) {
      setPlatform({ platformId: "claude-code" });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        생성된 솔루션을 실행할 Agent 플랫폼을 선택하세요.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {PLATFORM_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const isSelected = platformId === opt.id;
          const isAvailable = opt.available;

          return (
            <button
              key={opt.id}
              type="button"
              disabled={!isAvailable}
              onClick={() => isAvailable && setPlatform({ platformId: opt.id })}
              aria-pressed={isSelected}
              className={`relative flex items-start gap-3 rounded-xl border p-4 text-left transition-all duration-200 ${
                !isAvailable
                  ? "cursor-not-allowed border-zinc-100 bg-zinc-50 opacity-40"
                  : isSelected
                    ? "border-zinc-900 bg-zinc-50 ring-2 ring-zinc-900/10"
                    : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50"
              }`}
            >
              <span
                className={`absolute right-3 top-3 rounded-md px-1.5 py-0.5 text-xs font-medium ${
                  opt.badge === "추천"
                    ? "bg-emerald-100 text-emerald-600"
                    : "bg-zinc-100 text-zinc-500"
                }`}
              >
                {opt.badge}
              </span>
              <Icon
                className={`mt-0.5 h-5 w-5 shrink-0 ${isSelected ? "text-emerald-600" : "text-zinc-500"}`}
              />
              <div>
                <p
                  className={`text-sm font-semibold ${isSelected ? "text-zinc-950" : "text-zinc-700"}`}
                >
                  {opt.label}
                </p>
                <p className="mt-0.5 text-xs text-zinc-500">
                  {opt.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
      <p className="text-[11px] text-zinc-500">
        Gemini CLI · Cursor · Codex 지원은 추후 업데이트에서 제공될 예정입니다.
      </p>
    </div>
  );
}
