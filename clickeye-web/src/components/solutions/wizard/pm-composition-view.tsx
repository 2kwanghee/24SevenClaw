"use client";

import { Bot, Wrench, Webhook, Server, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";
import type {
  PMCompositionGroupedResponse,
  PMCompositionResponse,
  PMProfileResponse,
} from "@/lib/api-client";
import { usePMComposition } from "@/hooks/use-pm-profiles";

/** 위저드 PM 구성 미리보기 — 4그룹(에이전트/스킬/MCP/Hook).
 *  관리자 화면(composition-panel.tsx)과 동일하게 `GET /pm-profiles/{id}/composition`
 *  단일 API를 source-of-truth로 사용한다. plugin은 표시하지 않는다. */

type SectionKey = "agents" | "skills" | "mcp_servers" | "hooks";

const SECTIONS: {
  key: SectionKey;
  label: string;
  icon: typeof Bot;
  color: string;
  bg: string;
}[] = [
  {
    key: "agents",
    label: "AI 에이전트",
    icon: Bot,
    color: "text-emerald-700",
    bg: "bg-emerald-50",
  },
  {
    key: "skills",
    label: "스킬",
    icon: Wrench,
    color: "text-sky-700",
    bg: "bg-sky-50",
  },
  {
    key: "mcp_servers",
    label: "MCP 서버",
    icon: Server,
    color: "text-amber-700",
    bg: "bg-amber-50",
  },
  {
    key: "hooks",
    label: "Hook",
    icon: Webhook,
    color: "text-violet-700",
    bg: "bg-violet-50",
  },
];

interface PMCompositionViewProps {
  profile: PMProfileResponse;
  className?: string;
}

function chipLabel(item: PMCompositionResponse): string {
  return item.component_name?.trim() ? item.component_name : item.component_slug;
}

function totalItems(data: PMCompositionGroupedResponse | undefined): number {
  if (!data) return 0;
  return (
    data.agents.length +
    data.skills.length +
    data.mcp_servers.length +
    data.hooks.length
  );
}

export function PMCompositionView({ profile, className }: PMCompositionViewProps) {
  const { data, isLoading, isError } = usePMComposition(profile.id);

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

      {isLoading && (
        <div className="flex items-center gap-2 py-3 text-xs text-[var(--text-muted)]">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          구성 정보 불러오는 중...
        </div>
      )}

      {!isLoading && (isError || !data || totalItems(data) === 0) && (
        <p className="py-3 text-xs text-[var(--text-muted)]">
          구성된 항목이 없습니다.
        </p>
      )}

      {!isLoading && data && totalItems(data) > 0 && (
        <div className="space-y-3">
          {SECTIONS.map(({ key, label, icon: Icon, color, bg }) => {
            const items = data[key];
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
                    <span className="ml-1 text-[var(--text-muted)] opacity-70">
                      ({items.length})
                    </span>
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {items.map((item) => (
                      <span
                        key={item.id}
                        title={item.component_slug}
                        className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]"
                      >
                        {chipLabel(item)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
