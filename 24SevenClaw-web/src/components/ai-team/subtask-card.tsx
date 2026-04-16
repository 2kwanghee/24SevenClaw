"use client";

import {
  Bot,
  Code2,
  Cpu,
  Eye,
  Server,
  Shield,
  TestTube2,
  Wrench,
} from "lucide-react";

import type { SubTaskResponse } from "@/lib/api-client";

const ROLE_CONFIG: Record<
  string,
  { label: string; icon: React.ReactNode; color: string; bg: string }
> = {
  architect: {
    label: "아키텍트",
    icon: <Cpu className="h-3.5 w-3.5" />,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  frontend: {
    label: "프론트엔드",
    icon: <Code2 className="h-3.5 w-3.5" />,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
  },
  backend: {
    label: "백엔드",
    icon: <Server className="h-3.5 w-3.5" />,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  qa: {
    label: "QA",
    icon: <TestTube2 className="h-3.5 w-3.5" />,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  security: {
    label: "보안",
    icon: <Shield className="h-3.5 w-3.5" />,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  devops: {
    label: "DevOps",
    icon: <Wrench className="h-3.5 w-3.5" />,
    color: "text-orange-400",
    bg: "bg-orange-500/10",
  },
  reviewer: {
    label: "리뷰어",
    icon: <Eye className="h-3.5 w-3.5" />,
    color: "text-pink-400",
    bg: "bg-pink-500/10",
  },
};

const STATUS_CONFIG: Record<
  string,
  { label: string; cls: string }
> = {
  pending: { label: "대기", cls: "bg-slate-500/10 text-slate-400" },
  in_progress: { label: "진행 중", cls: "bg-blue-500/10 text-blue-400" },
  completed: { label: "완료", cls: "bg-emerald-500/10 text-emerald-400" },
  failed: { label: "실패", cls: "bg-red-500/10 text-red-400" },
  blocked: { label: "차단됨", cls: "bg-amber-500/10 text-amber-400" },
};

interface SubTaskCardProps {
  subtask: SubTaskResponse;
}

export function SubTaskCard({ subtask }: SubTaskCardProps) {
  const role = ROLE_CONFIG[subtask.assigned_role] ?? {
    label: subtask.assigned_role,
    icon: <Bot className="h-3.5 w-3.5" />,
    color: "text-slate-400",
    bg: "bg-slate-500/10",
  };
  const status = STATUS_CONFIG[subtask.status] ?? STATUS_CONFIG.pending;

  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:bg-white/[0.04]">
      {/* 역할 배지 + 상태 */}
      <div className="flex items-center justify-between">
        <div className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${role.bg} ${role.color}`}>
          {role.icon}
          {role.label}
        </div>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${status.cls}`}>
          {status.label}
        </span>
      </div>

      {/* 제목 */}
      <p className="mt-3 text-sm font-medium text-slate-200 line-clamp-2">
        {subtask.title}
      </p>

      {/* 미리보기 (result_summary 또는 description) */}
      {(subtask.result_summary || subtask.description) && (
        <p className="mt-1.5 text-xs text-slate-500 line-clamp-2">
          {subtask.result_summary ?? subtask.description}
        </p>
      )}

      {/* 의존성 표시 */}
      {subtask.depends_on.length > 0 && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-slate-600">
          <span>의존:</span>
          <span className="truncate">{subtask.depends_on.length}개 태스크</span>
        </div>
      )}
    </div>
  );
}
