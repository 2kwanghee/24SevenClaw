"use client";

import { FolderPlus } from "lucide-react";
import Link from "next/link";

import type { ProjectResponse } from "@/lib/api-client";

import { ProjectCard } from "./project-card";

interface ProjectListProps {
  projects: ProjectResponse[];
}

export function ProjectList({ projects }: ProjectListProps) {
  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 py-20">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-500/10">
          <FolderPlus className="h-7 w-7 text-violet-400" />
        </div>
        <p className="mt-4 text-sm font-medium text-slate-300">
          아직 프로젝트가 없습니다
        </p>
        <p className="mt-1 text-sm text-slate-500">
          첫 번째 프로젝트를 생성하여 시작하세요
        </p>
        <Link
          href="/solutions/new"
          className="mt-6 rounded-xl bg-violet-600 px-6 py-2.5 text-sm font-medium text-white shadow-lg shadow-violet-600/25 transition-all hover:bg-violet-500"
        >
          새 프로젝트 만들기
        </Link>
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
