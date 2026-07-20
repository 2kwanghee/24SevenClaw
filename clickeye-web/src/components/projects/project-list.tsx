"use client";

import { FolderPlus } from "lucide-react";
import Link from "next/link";

import type { ProjectResponse } from "@/lib/api-client";

import { ProjectCard } from "./project-card";

interface ProjectListProps {
  projects: ProjectResponse[];
  /** 빈 상태 CTA에서 프로젝트 생성 다이얼로그를 열기 위한 핸들러. */
  onCreate?: () => void;
}

export function ProjectList({ projects, onCreate }: ProjectListProps) {
  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border-subtle)] py-20">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--bg-hover)]">
          <FolderPlus className="h-7 w-7 text-[var(--text-secondary)]" />
        </div>
        <p className="mt-4 text-sm font-medium text-[var(--text-secondary)]">
          아직 프로젝트가 없습니다
        </p>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          첫 번째 프로젝트를 생성하여 시작하세요
        </p>
        {onCreate ? (
          <button
            type="button"
            onClick={onCreate}
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-zinc-900 px-6 py-2.5 text-sm font-medium text-white shadow-lg transition-all hover:bg-zinc-800"
          >
            <FolderPlus className="h-4 w-4" />
            새 프로젝트
          </button>
        ) : (
          <Link
            href="/delivery"
            className="mt-6 rounded-xl bg-zinc-900 px-6 py-2.5 text-sm font-medium text-white shadow-lg transition-all hover:bg-zinc-800"
          >
            딜리버리 콘솔로 이동
          </Link>
        )}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}
