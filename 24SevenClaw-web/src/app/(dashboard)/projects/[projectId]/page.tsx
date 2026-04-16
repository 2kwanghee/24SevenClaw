"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { useSession } from "next-auth/react";
import {
  ArrowLeft,
  BarChart3,
  Settings,
  Trash2,
  Pencil,
  X,
  AlertCircle,
  Calendar,
  Activity,
  Download,
  Loader2,
  Bot,
  Wrench,
  GitBranch,
  Monitor,
  Layers,
  Building2,
} from "lucide-react";

import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog";
import { ProjectForm } from "@/components/projects/project-form";
import {
  useDeleteProject,
  useProject,
  useUpdateProject,
} from "@/hooks/use-projects";
import { apiClient, ApiClientError } from "@/lib/api-client";

const SOLUTION_TYPE_LABELS: Record<string, string> = {
  saas: "SaaS",
  "rest-api": "REST API",
  fullstack: "풀스택",
  "internal-tool": "내부 도구",
  mvp: "MVP",
  custom: "커스텀",
};

const PLATFORM_LABELS: Record<string, string> = {
  "claude-code": "Claude Code",
  "gemini-cli": "Gemini CLI",
  codex: "Codex",
  cursor: "Cursor",
};

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const { data: project, isLoading, error } = useProject(projectId);
  const updateProject = useUpdateProject(projectId);
  const deleteProject = useDeleteProject();

  const [isEditing, setIsEditing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleRedownload = useCallback(async () => {
    if (!token || !projectId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await apiClient.projects.redownload(token, projectId, {
        env_vars: {},
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.name || "project"}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setDownloadError(err.detail);
      } else {
        setDownloadError("재다운로드에 실패했습니다");
      }
    } finally {
      setDownloading(false);
    }
  }, [token, projectId, project?.name]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        <p className="mt-4 text-sm text-slate-500">불러오는 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center">
        <p className="text-sm text-red-300">
          프로젝트를 불러오지 못했습니다: {error.message}
        </p>
      </div>
    );
  }

  if (!project) return null;

  const formattedDate = new Date(project.created_at).toLocaleDateString(
    "ko-KR",
    { year: "numeric", month: "long", day: "numeric" },
  );

  const isActive = project.status === "active";

  return (
    <div>
      {/* 브레드크럼 */}
      <div className="mb-8">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-slate-300"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          프로젝트 목록
        </Link>
      </div>

      {isEditing ? (
        /* 수정 모드 */
        <div className="mx-auto max-w-lg rounded-2xl border border-white/5 bg-white/[0.02] p-8">

          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">프로젝트 수정</h2>
            <button
              onClick={() => setIsEditing(false)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {submitError && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
              <p className="text-sm text-red-300">{submitError}</p>
            </div>
          )}

          <ProjectForm
            defaultValues={{
              name: project.name,
              description: project.description ?? "",
            }}
            isSubmitting={updateProject.isPending}
            submitLabel="저장"
            onSubmit={(data) => {
              setSubmitError(null);
              updateProject.mutate(
                { ...data, description: data.description || undefined },
                {
                  onSuccess: () => setIsEditing(false),
                  onError: (err) => {
                    if (err instanceof ApiClientError) {
                      setSubmitError(err.detail);
                    } else {
                      setSubmitError("수정에 실패했습니다.");
                    }
                  },
                },
              );
            }}
          />
        </div>
      ) : (
        /* 상세 보기 */
        <>
        <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-8">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-white">{project.name}</h1>
                <span
                  className={`rounded-md px-2.5 py-0.5 text-xs font-medium ${
                    isActive
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-slate-500/10 text-slate-400"
                  }`}
                >
                  {isActive ? "활성" : "보관됨"}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-500">{project.slug}</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setSubmitError(null);
                  setIsEditing(true);
                }}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
              >
                <Pencil className="h-3.5 w-3.5" />
                수정
              </button>
              <Link
                href={`/projects/${projectId}/dashboard`}
                className="flex items-center gap-2 rounded-xl border border-violet-500/20 bg-violet-500/5 px-4 py-2 text-sm font-medium text-violet-300 transition-all hover:bg-violet-500/10"
              >
                <BarChart3 className="h-3.5 w-3.5" />
                대시보드
              </Link>
              <Link
                href={`/projects/${projectId}/ai-team`}
                className="flex items-center gap-2 rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-2 text-sm font-medium text-cyan-300 transition-all hover:bg-cyan-500/10"
              >
                <Bot className="h-3.5 w-3.5" />
                AI Team
              </Link>
              <Link
                href={`/projects/${projectId}/settings`}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
              >
                <Settings className="h-3.5 w-3.5" />
                설정
              </Link>
              <button
                onClick={() => setDeleteOpen(true)}
                className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-2 text-sm font-medium text-red-400 transition-all hover:bg-red-500/10"
              >
                <Trash2 className="h-3.5 w-3.5" />
                삭제
              </button>
            </div>
          </div>

          {project.description && (
            <p className="mt-6 leading-relaxed text-slate-300">
              {project.description}
            </p>
          )}

          {/* 메타 정보 */}
          <div className="mt-8 flex gap-6 border-t border-white/5 pt-6">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Calendar className="h-4 w-4" />
              생성일: {formattedDate}
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Activity className="h-4 w-4" />
              상태: {isActive ? "활성" : "보관됨"}
            </div>
          </div>
        </div>

        {/* 설정 요약 */}
        {project.wizard_data && (
          <div className="mt-6 rounded-2xl border border-white/5 bg-white/[0.02] p-8">
            <h2 className="mb-4 text-lg font-semibold text-white">
              설정 요약
            </h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <ConfigBadge
                icon={Building2}
                label="회사"
                value={
                  (project.wizard_data.organization?.companyName as string) ||
                  "미설정"
                }
              />
              <ConfigBadge
                icon={Layers}
                label="솔루션"
                value={
                  project.wizard_data.solution?.solutionType
                    ? SOLUTION_TYPE_LABELS[
                        project.wizard_data.solution.solutionType as string
                      ] ?? (project.wizard_data.solution.solutionType as string)
                    : "미설정"
                }
              />
              <ConfigBadge
                icon={Bot}
                label="에이전트"
                value={
                  project.wizard_data.agents?.length > 0
                    ? `${project.wizard_data.agents.length}개`
                    : "미설정"
                }
              />
              <ConfigBadge
                icon={Wrench}
                label="스킬"
                value={
                  project.wizard_data.skills?.length > 0
                    ? `${project.wizard_data.skills.length}개`
                    : "미설정"
                }
              />
              <ConfigBadge
                icon={GitBranch}
                label="파이프라인"
                value={
                  project.wizard_data.pipelines?.length > 0
                    ? `${project.wizard_data.pipelines.length}개`
                    : "미설정"
                }
              />
              <ConfigBadge
                icon={Monitor}
                label="플랫폼"
                value={
                  project.wizard_data.platform?.platformId
                    ? PLATFORM_LABELS[
                        project.wizard_data.platform.platformId as string
                      ] ??
                      (project.wizard_data.platform.platformId as string)
                    : "미설정"
                }
              />
            </div>

            {/* 재다운로드 */}
            <div className="mt-6 flex items-center gap-3 border-t border-white/5 pt-6">
              <button
                onClick={handleRedownload}
                disabled={downloading}
                className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {downloading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    다운로드 중...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" />
                    ZIP 재다운로드
                  </>
                )}
              </button>
              <span className="text-xs text-slate-500">
                저장된 설정으로 동일한 ZIP을 다시 생성합니다
              </span>
            </div>
            {downloadError && (
              <div className="mt-3 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
                <AlertCircle className="h-3.5 w-3.5 text-red-400" />
                <p className="text-xs text-red-300">{downloadError}</p>
              </div>
            )}
          </div>
        )}
        </>
      )}

      <DeleteProjectDialog
        projectName={project.name}
        isOpen={deleteOpen}
        isDeleting={deleteProject.isPending}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => {
          deleteProject.mutate(projectId, {
            onSuccess: () => router.push("/projects"),
            onError: () => setDeleteOpen(false),
          });
        }}
      />
    </div>
  );
}

/* ── 설정 요약 배지 ── */

interface ConfigBadgeProps {
  icon: typeof Building2;
  label: string;
  value: string;
}

function ConfigBadge({ icon: Icon, label, value }: ConfigBadgeProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2">
      <Icon className="h-3.5 w-3.5 shrink-0 text-violet-400/60" />
      <div className="min-w-0">
        <p className="text-[10px] text-slate-600">{label}</p>
        <p className="truncate text-xs font-medium text-slate-300">{value}</p>
      </div>
    </div>
  );
}
