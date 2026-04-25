import Link from "next/link";
import { FolderKanban, Calendar, ArrowUpRight, Cpu, ThumbsUp, FileCheck } from "lucide-react";

import type { ProjectResponse } from "@/lib/api-client";

export interface ProjectKpiSummary {
  automationRate: number;
  reviewAcceptanceRate: number;
  totalArtifacts: number;
  releasedArtifacts: number;
}

interface ProjectCardProps {
  project: ProjectResponse;
  kpi?: ProjectKpiSummary;
}

export function ProjectCard({ project, kpi }: ProjectCardProps) {
  const isActive = project.status === "active";

  const formattedDate = new Date(project.created_at).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <Link
      href={`/projects/${project.id}`}
      className="group relative rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 transition-all hover:border-zinc-300 hover:bg-[var(--bg-hover)] hover:shadow-lg"
    >
      {/* 호버 시 화살표 */}
      <ArrowUpRight className="absolute right-4 top-4 h-4 w-4 text-[var(--text-muted)] opacity-0 transition-all group-hover:text-[var(--text-secondary)] group-hover:opacity-100" />

      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
          <FolderKanban className="h-5 w-5 text-[var(--text-secondary)]" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-base font-semibold text-[var(--text-primary)]">
              {project.name}
            </h3>
            <span
              className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-medium ${
                isActive
                  ? "bg-[var(--bg-hover)] text-[var(--text-secondary)]"
                  : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
              }`}
            >
              {isActive ? "활성" : "보관됨"}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-[var(--text-muted)]">{project.slug}</p>
        </div>
      </div>

      {project.description && (
        <p className="mt-4 line-clamp-2 text-sm leading-relaxed text-[var(--text-muted)]">
          {project.description}
        </p>
      )}

      {/* KPI 미니 스트립 */}
      {kpi && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2">
          <div className="flex items-center gap-1" title="자동화율">
            <Cpu className="h-3 w-3 text-[var(--text-secondary)]" />
            <span className="text-xs font-medium text-[var(--text-secondary)]">
              {Math.round(kpi.automationRate)}%
            </span>
          </div>
          <div className="h-3 w-px bg-[var(--border-subtle)]" />
          <div className="flex items-center gap-1" title="리뷰 수락율">
            <ThumbsUp className="h-3 w-3 text-[var(--text-secondary)]" />
            <span className="text-xs font-medium text-[var(--text-secondary)]">
              {Math.round(kpi.reviewAcceptanceRate)}%
            </span>
          </div>
          <div className="h-3 w-px bg-[var(--border-subtle)]" />
          <div className="flex items-center gap-1" title="배포된 산출물">
            <FileCheck className="h-3 w-3 text-[var(--text-secondary)]" />
            <span className="text-xs font-medium text-[var(--text-secondary)]">
              {kpi.releasedArtifacts}/{kpi.totalArtifacts}
            </span>
          </div>
        </div>
      )}

      <div className="mt-4 flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
        <Calendar className="h-3 w-3" />
        {formattedDate}
      </div>
    </Link>
  );
}
