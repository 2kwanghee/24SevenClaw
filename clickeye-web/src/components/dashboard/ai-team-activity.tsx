"use client";

import {
  Bot,
  Code2,
  Shield,
  TestTube2,
  Wrench,
  Eye,
  Server,
  Cpu,
} from "lucide-react";

import type { AITeamActivity as AITeamActivityType } from "@/lib/api-client";

const ROLE_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  architect: { label: "아키텍트", icon: <Cpu className="h-3.5 w-3.5" />, color: "text-zinc-700" },
  frontend: { label: "프론트엔드", icon: <Code2 className="h-3.5 w-3.5" />, color: "text-cyan-700" },
  backend: { label: "백엔드", icon: <Server className="h-3.5 w-3.5" />, color: "text-blue-700" },
  qa: { label: "QA", icon: <TestTube2 className="h-3.5 w-3.5" />, color: "text-emerald-700" },
  security: { label: "보안", icon: <Shield className="h-3.5 w-3.5" />, color: "text-amber-700" },
  devops: { label: "DevOps", icon: <Wrench className="h-3.5 w-3.5" />, color: "text-orange-700" },
  reviewer: { label: "리뷰어", icon: <Eye className="h-3.5 w-3.5" />, color: "text-pink-700" },
  agent: { label: "에이전트", icon: <Bot className="h-3.5 w-3.5" />, color: "text-indigo-700" },
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-zinc-100 text-zinc-600",
  in_progress: "bg-blue-50 text-blue-700",
  completed: "bg-emerald-50 text-emerald-700",
  failed: "bg-red-50 text-red-700",
  blocked: "bg-amber-50 text-amber-700",
};

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "방금 전";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  return `${days}일 전`;
}

interface AITeamActivityProps {
  data: AITeamActivityType[];
}

export function AITeamActivity({ data }: AITeamActivityProps) {
  return (
    <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
      <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">
        AI 팀 활동 로그
      </h3>

      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-[var(--text-muted)]">
          아직 활동 기록이 없습니다
        </p>
      ) : (
        <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
          {data.map((item, i) => {
            const roleCfg = ROLE_CONFIG[item.role] ?? {
              label: item.role,
              icon: <Bot className="h-3.5 w-3.5" />,
              color: "text-[var(--text-muted)]",
            };
            const badgeCls = STATUS_BADGE[item.status] ?? "bg-zinc-100 text-zinc-600";

            return (
              <div
                key={`${item.timestamp}-${i}`}
                className="flex items-start gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-3"
              >
                <div className={`mt-0.5 ${roleCfg.color}`}>
                  {roleCfg.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${roleCfg.color}`}>
                      {roleCfg.label}
                    </span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${badgeCls}`}>
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-sm text-[var(--text-primary)]">
                    {item.title}
                  </p>
                  {item.message && (
                    <p className="mt-0.5 truncate text-xs text-[var(--text-muted)]">
                      {item.message}
                    </p>
                  )}
                </div>
                <span className="shrink-0 text-[10px] text-[var(--text-muted)]">
                  {formatRelativeTime(item.timestamp)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
