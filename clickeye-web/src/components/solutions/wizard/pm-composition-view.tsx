"use client";

import { Bot, Wrench, Webhook, Server, Puzzle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PMProfileResponse } from "@/lib/api-client";

interface CompositionData {
  agents: string[];
  skills: string[];
  hooks: string[];
  mcp_servers: string[];
  plugins: string[];
}

const MCP_SKILL_NAMES = new Set([
  "linear",
  "github",
  "slack",
  "jira",
  "notion",
  "telegram",
  "figma",
]);

/** PMProfileResponse에서 구성 요소를 파생한다 */
function deriveComposition(profile: PMProfileResponse): CompositionData {
  const traits = profile.personality as Record<string, unknown>;

  const agents =
    (traits.agents as string[] | undefined) ??
    profile.specialties
      .slice(0, 3)
      .map((a) => a.toLowerCase().replace(/\s+/g, "-"));

  const skills =
    (traits.skills as string[] | undefined) ?? profile.specialties;

  const hooks =
    (traits.hooks as string[] | undefined) ?? ["pre-commit", "test-runner"];

  const mcp_servers =
    (traits.mcp_servers as string[] | undefined) ??
    profile.specialties.filter((s) => MCP_SKILL_NAMES.has(s.toLowerCase()));

  const plugins =
    (traits.plugins as string[] | undefined) ?? ["code-review"];

  return { agents, skills, hooks, mcp_servers, plugins };
}

const SECTIONS = [
  {
    key: "agents" as const,
    label: "AI 에이전트",
    icon: Bot,
    color: "text-emerald-700",
    bg: "bg-emerald-50",
  },
  {
    key: "skills" as const,
    label: "스킬",
    icon: Wrench,
    color: "text-sky-700",
    bg: "bg-sky-50",
  },
  {
    key: "hooks" as const,
    label: "훅",
    icon: Webhook,
    color: "text-violet-700",
    bg: "bg-violet-50",
  },
  {
    key: "mcp_servers" as const,
    label: "MCP 서버",
    icon: Server,
    color: "text-amber-700",
    bg: "bg-amber-50",
  },
  {
    key: "plugins" as const,
    label: "플러그인",
    icon: Puzzle,
    color: "text-rose-700",
    bg: "bg-rose-50",
  },
] as const;

interface PMCompositionViewProps {
  profile: PMProfileResponse;
  className?: string;
}

export function PMCompositionView({ profile, className }: PMCompositionViewProps) {
  const composition = deriveComposition(profile);

  return (
    <div
      className={cn(
        "rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-4",
        className,
      )}
    >
      <p className="mb-3 text-xs font-medium text-[var(--text-muted)]">
        {profile.name} 구성 요소
      </p>
      <div className="space-y-3">
        {SECTIONS.map(({ key, label, icon: Icon, color, bg }) => {
          const items = composition[key];
          if (!items || items.length === 0) return null;
          return (
            <div key={key} className="flex items-start gap-3">
              <div
                className={cn(
                  "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
                  bg,
                )}
              >
                <Icon className={cn("h-3.5 w-3.5", color)} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="mb-1 text-[11px] font-medium text-[var(--text-muted)]">
                  {label}
                </p>
                <div className="flex flex-wrap gap-1">
                  {items.map((item) => (
                    <span
                      key={item}
                      className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
