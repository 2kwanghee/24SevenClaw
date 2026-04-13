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
  architect: { label: "아키텍트", icon: <Cpu className="h-3.5 w-3.5" />, color: "text-violet-400" },
  frontend: { label: "프론트엔드", icon: <Code2 className="h-3.5 w-3.5" />, color: "text-cyan-400" },
  backend: { label: "백엔드", icon: <Server className="h-3.5 w-3.5" />, color: "text-blue-400" },
  qa: { label: "QA", icon: <TestTube2 className="h-3.5 w-3.5" />, color: "text-emerald-400" },
  security: { label: "보안", icon: <Shield className="h-3.5 w-3.5" />, color: "text-amber-400" },
  devops: { label: "DevOps", icon: <Wrench className="h-3.5 w-3.5" />, color: "text-orange-400" },
  reviewer: { label: "리뷰어", icon: <Eye className="h-3.5 w-3.5" />, color: "text-pink-400" },
  agent: { label: "에이전트", icon: <Bot className="h-3.5 w-3.5" />, color: "text-indigo-400" },
};

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-slate-500/10 text-slate-400",
  in_progress: "bg-blue-500/10 text-blue-400",
  completed: "bg-emerald-500/10 text-emerald-400",
  failed: "bg-red-500/10 text-red-400",
  blocked: "bg-amber-500/10 text-amber-400",
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
    <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
      <h3 className="mb-4 text-sm font-semibold text-slate-200">
        AI 팀 활동 로그
      </h3>

      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">
          아직 활동 기록이 없습니다
        </p>
      ) : (
        <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
          {data.map((item, i) => {
            const roleCfg = ROLE_CONFIG[item.role] ?? {
              label: item.role,
              icon: <Bot className="h-3.5 w-3.5" />,
              color: "text-slate-400",
            };
            const badgeCls = STATUS_BADGE[item.status] ?? "bg-slate-500/10 text-slate-400";

            return (
              <div
                key={`${item.timestamp}-${i}`}
                className="flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-3"
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
                  <p className="mt-0.5 truncate text-sm text-slate-300">
                    {item.title}
                  </p>
                  {item.message && (
                    <p className="mt-0.5 truncate text-xs text-slate-500">
                      {item.message}
                    </p>
                  )}
                </div>
                <span className="shrink-0 text-[10px] text-slate-600">
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
