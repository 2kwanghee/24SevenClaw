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
  CheckCircle2,
  XCircle,
  RefreshCw,
  ExternalLink,
  Zap,
} from "lucide-react";

import { useQuery } from "@tanstack/react-query";

import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog";
import { ProjectForm } from "@/components/projects/project-form";
import { PMFeedbackCard } from "@/components/projects/pm-feedback-card";
import {
  useDeleteProject,
  useProject,
  useUpdateProject,
} from "@/hooks/use-projects";
import { apiClient, ApiClientError, linearCredentials, type LinearConnectionStatus } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

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
  // API 키 — 위저드 스토어에서 초기값 로드 (보안상 DB 저장 안 함)
  const [envVars, setEnvVars] = useState<Record<string, string>>(() => {
    const stored = useSolutionWizardStore.getState().data.env.envVars;
    return { ...stored };
  });

  const { data: linearStatus, refetch: refetchLinearStatus, isFetching: linearFetching } = useQuery({
    queryKey: ["linear-connection-status"],
    queryFn: () => linearCredentials.status(token),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });

  const handleRedownload = useCallback(async () => {
    if (!token || !projectId) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await apiClient.projects.redownload(token, projectId, {
        env_vars: Object.fromEntries(
          Object.entries(envVars).filter(([, v]) => v.trim() !== "")
        ),
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
  }, [token, projectId, project?.name, envVars]);

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

        {/* 설정 요약 + ZIP 다운로드 (wizard 프로젝트) */}
        {(project.wizard_data || project.project_type === "wizard") && (
          <div className="mt-6 rounded-2xl border border-white/5 bg-white/[0.02] p-8">
            <h2 className="mb-4 text-lg font-semibold text-white">
              설정 요약
            </h2>

            {project.wizard_data ? (
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
            ) : (
              <p className="text-sm text-slate-500">
                위저드 설정 정보가 없습니다. ZIP을 다시 생성하려면 솔루션 위저드를 다시 진행해 주세요.
              </p>
            )}

            {/* ZIP 재다운로드 — API 키 입력 + 다운로드 */}
            {project.wizard_data && (() => {
              const skillIds: string[] = (project.wizard_data.skills ?? []).map(
                (s: { id: string }) => s.id
              );
              const hasLinear = skillIds.includes("linear");
              const hasNotion = skillIds.includes("notion");

              const ENV_FIELDS: { key: string; label: string; placeholder: string }[] = [
                { key: "ANTHROPIC_API_KEY", label: "Anthropic API Key", placeholder: "sk-ant-..." },
                ...(hasLinear
                  ? [
                      { key: "LINEAR_API_KEY", label: "Linear API Key", placeholder: "lin_api_..." },
                      { key: "LINEAR_TEAM_ID", label: "Linear Team ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" },
                    ]
                  : []),
                ...(hasNotion
                  ? [
                      { key: "NOTION_API_KEY", label: "Notion API Key", placeholder: "secret_..." },
                      { key: "NOTION_DATABASE_ID", label: "Notion Database ID", placeholder: "xxxxxxxx-xxxx-..." },
                    ]
                  : []),
              ];

              return (
                <div className="mt-6 border-t border-white/5 pt-6 space-y-4">
                  <p className="text-xs text-slate-400">
                    API 키는 서버에 저장되지 않습니다. ZIP의 <code className="text-slate-300">.env</code>에 직접 작성됩니다.
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {ENV_FIELDS.map(({ key, label, placeholder }) => (
                      <div key={key}>
                        <label className="mb-1 block text-[11px] font-medium text-slate-400">
                          {label}
                        </label>
                        <input
                          type="text"
                          value={envVars[key] ?? ""}
                          onChange={(e) =>
                            setEnvVars((prev) => ({ ...prev, [key]: e.target.value }))
                          }
                          placeholder={placeholder}
                          className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs text-slate-200 placeholder-slate-600 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/30"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleRedownload}
                      disabled={downloading || !envVars["ANTHROPIC_API_KEY"]?.trim()}
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
                          ZIP 다운로드
                        </>
                      )}
                    </button>
                    <span className="text-xs text-slate-500">
                      저장된 설정 + 입력한 API 키로 ZIP을 생성합니다
                    </span>
                  </div>
                  {downloadError && (
                    <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
                      <AlertCircle className="h-3.5 w-3.5 text-red-400" />
                      <p className="text-xs text-red-300">{downloadError}</p>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}

        {/* PM 피드백 카드 (wizard 프로젝트이고 PM이 배정된 경우) */}
        {project.pm_profile_id && project.prototype_session_id && (
          <PMFeedbackCard
            projectId={projectId}
            pmProfileId={project.pm_profile_id}
            sessionId={project.prototype_session_id}
          />
        )}

        {/* Linear 연동 프리플라이트 카드 */}
        <LinearPreflightCard
          projectId={projectId}
          status={linearStatus ?? null}
          isFetching={linearFetching}
          onRefresh={() => void refetchLinearStatus()}
        />
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

/* -- 설정 요약 배지 -- */

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

/* -- Linear 연동 프리플라이트 카드 -- */

interface LinearPreflightCardProps {
  projectId: string;
  status: LinearConnectionStatus | null;
  isFetching: boolean;
  onRefresh: () => void;
}

interface CheckItemProps {
  ok: boolean | null;
  label: string;
  description?: string;
}

function CheckItem({ ok, label, description }: CheckItemProps) {
  return (
    <div className="flex items-start gap-3">
      {ok === null ? (
        <div className="mt-0.5 h-4 w-4 shrink-0 animate-pulse rounded-full bg-slate-700" />
      ) : ok ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
      ) : (
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
      )}
      <div>
        <p className="text-sm font-medium text-slate-300">{label}</p>
        {description && <p className="text-xs text-slate-500">{description}</p>}
      </div>
    </div>
  );
}

function LinearPreflightCard({ projectId, status, isFetching, onRefresh }: LinearPreflightCardProps) {
  const allReady =
    status?.credentials_saved &&
    status?.tunnel_url != null &&
    status?.tunnel_reachable === true &&
    status?.webhook_registered;

  return (
    <div className="mt-6 rounded-2xl border border-white/5 bg-white/[0.02] p-8">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-violet-400" />
          <h2 className="text-lg font-semibold text-white">Linear 연동 준비 상태</h2>
        </div>
        <button
          onClick={onRefresh}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-400 transition-all hover:bg-white/10 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          새로고침
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CheckItem
          ok={status ? status.credentials_saved : null}
          label="자격증명 저장됨"
          description={
            status?.credentials_saved
              ? status.team_name ? `팀: ${status.team_name}` : "Linear API 키가 등록되어 있습니다"
              : "Linear API 키와 팀 ID를 등록해 주세요"
          }
        />
        <CheckItem
          ok={status ? status.tunnel_url != null : null}
          label="터널 URL 등록됨"
          description={
            status?.tunnel_url
              ? status.tunnel_url
              : "cloudflared 터널 URL을 설정에서 등록해 주세요"
          }
        />
        <CheckItem
          ok={status ? status.tunnel_reachable === true : null}
          label="터널 응답 확인됨"
          description={
            status?.tunnel_reachable === true
              ? "webhook 서버가 외부에서 접근 가능합니다"
              : status?.tunnel_url
              ? "터널이 응답하지 않습니다. start-webhook.sh를 실행해 주세요"
              : "터널 URL 등록 후 확인 가능합니다"
          }
        />
        <CheckItem
          ok={status ? status.webhook_registered : null}
          label="Linear Webhook 등록됨"
          description={
            status?.webhook_registered
              ? "Linear에서 이벤트를 수신할 준비가 되었습니다"
              : "설정에서 터널 URL 저장 시 자동으로 등록됩니다"
          }
        />
      </div>

      <div className="mt-6 flex items-center gap-3 border-t border-white/5 pt-6">
        {allReady ? (
          <a
            href={`/projects/${projectId}/ai-team`}
            className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500"
          >
            <Zap className="h-4 w-4" />
            AI Team 시작하기
          </a>
        ) : (
          <a
            href="/settings/linear"
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Linear 설정 바로가기
          </a>
        )}
        <span className="text-xs text-slate-500">
          {allReady
            ? "모든 준비가 완료되었습니다. AI Team에서 Linear 이슈를 자동으로 생성할 수 있습니다."
            : "4가지 항목을 모두 완료하면 Linear 자동화가 활성화됩니다."}
        </span>
      </div>
    </div>
  );
}
