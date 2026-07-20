"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import {
  ArrowLeft,
  BarChart3,
  Settings,
  Trash2,
  Pencil,
  X,
  AlertCircle,
  AlertTriangle,
  Calendar,
  Activity,
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
  RotateCcw,
} from "lucide-react";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog";
import { ResetProjectDialog } from "@/components/projects/reset-project-dialog";
import { ProjectForm } from "@/components/projects/project-form";
import { PMFeedbackCard } from "@/components/projects/pm-feedback-card";
import {
  useDeleteProject,
  useProject,
  useUpdateProject,
} from "@/hooks/use-projects";
import { apiClient, ApiClientError, projectLinearCredentials, type ProjectLinearStatus } from "@/lib/api-client";

const SOLUTION_TYPE_LABELS: Record<string, string> = {
  saas: "SaaS",
  "rest-api": "REST API",
  mvp: "MVP",
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
  const tD = useTranslations("projects.detail");
  const { data: project, isLoading, error } = useProject(projectId);
  const updateProject = useUpdateProject(projectId);
  const deleteProject = useDeleteProject();

  const [isEditing, setIsEditing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetResult, setResetResult] = useState<{ new_license_key: string | null } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  /* --------------------------------------------------------------
    Linear 연동 프리플라이트 — 자격증명 저장 상태 확인
  -------------------------------------------------------------- */
  const skillIds = useMemo<string[]>(
    () => ((project?.wizard_data?.skills ?? []) as { id: string }[]).map((s) => s.id),
    [project?.wizard_data?.skills],
  );
  const hasLinear = skillIds.includes("linear");

  const { data: linearStatus, refetch: refetchLinearStatus, isFetching: linearFetching } = useQuery({
    queryKey: ["linear-connection-status", projectId],
    queryFn: () => projectLinearCredentials.status(token, projectId),
    enabled: !!token && !!projectId,
    staleTime: 5 * 60 * 1000,
  });

  const handleReset = useCallback(async () => {
    if (!token || !projectId) return;
    setResetting(true);
    try {
      const result = await apiClient.projects.reset(token, projectId);
      setResetResult({ new_license_key: result.new_license_key });
      setResetOpen(false);
    } catch {
      setResetOpen(false);
    } finally {
      setResetting(false);
    }
  }, [token, projectId]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--border-medium)] border-t-[var(--accent)]" />
        <p className="mt-4 text-sm text-[var(--text-muted)]">{tD("loading")}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">
          {tD("loadError", { message: error.message })}
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
  const isStale =
    project.anthropic_key_status === "stale" || project.linear_key_status === "stale";
  const resolveSolutionTypeLabel = (solutionType?: string | null) => {
    if (!solutionType) return tD("notSet");
    if (solutionType === "fullstack") return tD("solutionTypeFullstack");
    if (solutionType === "internal-tool") return tD("solutionTypeInternalTool");
    if (solutionType === "custom") return tD("solutionTypeCustom");
    return SOLUTION_TYPE_LABELS[solutionType] ?? solutionType;
  };

  return (
    <div>
      {/* 브레드크럼 */}
      <div className="mb-8">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {tD("backToList")}
        </Link>
      </div>

      {/* Stale 키 갱신 안내 배너 */}
      {isStale && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600" />
          <div>
            <p className="text-sm font-medium text-amber-800">{tD("staleKeyTitle")}</p>
            <p className="mt-0.5 text-xs text-amber-700">
              {tD("staleKeyDesc", {
                keys: [
                  project.anthropic_key_status === "stale" ? tD("staleKeyAnthropicLabel") : null,
                  project.linear_key_status === "stale" ? tD("staleKeyLinearLabel") : null,
                ].filter(Boolean).join(", "),
              })}
            </p>
          </div>
        </div>
      )}

      {isEditing ? (
        /* 수정 모드 */
        <div className="mx-auto max-w-lg rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">

          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">{tD("editTitle")}</h2>
            <button
              onClick={() => setIsEditing(false)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {submitError && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
              <p className="text-sm text-red-700">{submitError}</p>
            </div>
          )}

          <ProjectForm
            defaultValues={{
              name: project.name,
              description: project.description ?? "",
            }}
            isSubmitting={updateProject.isPending}
            submitLabel={tD("submitLabel")}
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
                      setSubmitError(tD("editFail"));
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
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-[var(--text-primary)]">{project.name}</h1>
                <span
                  className={`rounded-md px-2.5 py-0.5 text-xs font-medium ${
                    isActive
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
                  }`}
                >
                  {isActive ? tD("statusActive") : tD("statusArchived")}
                </span>
              </div>
              <p className="mt-1 text-sm text-[var(--text-muted)]">{project.slug}</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setSubmitError(null);
                  setIsEditing(true);
                }}
                className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <Pencil className="h-3.5 w-3.5" />
                {tD("editBtn")}
              </button>
              <Link
                href={`/projects/${projectId}/dashboard`}
                className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <BarChart3 className="h-3.5 w-3.5" />
                {tD("dashboardBtn")}
              </Link>
              <Link
                href={`/projects/${projectId}/ai-team`}
                className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <Bot className="h-3.5 w-3.5" />
                AI Team
              </Link>
              <Link
                href={`/projects/${projectId}/settings`}
                className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <Settings className="h-3.5 w-3.5" />
                {tD("settingsBtn")}
              </Link>
            </div>
          </div>

          {project.description && (
            <p className="mt-6 leading-relaxed text-[var(--text-secondary)]">
              {project.description}
            </p>
          )}

          {/* 메타 정보 */}
          <div className="mt-8 flex gap-6 border-t border-[var(--border-subtle)] pt-6">
            <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
              <Calendar className="h-4 w-4" />
              {tD("createdAt", { date: formattedDate })}
            </div>
            <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
              <Activity className="h-4 w-4" />
              {tD("statusMeta", { status: isActive ? tD("statusActive") : tD("statusArchived") })}
            </div>
          </div>
        </div>

        {/* 설정 요약 (wizard 프로젝트) */}
        {(project.wizard_data || project.project_type === "wizard") && (
          <div className="mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
              {tD("configSummary")}
            </h2>

            {project.wizard_data ? (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <ConfigBadge
                  icon={Building2}
                  label={tD("labelCompany")}
                  value={
                    (project.wizard_data.organization?.companyName as string) ||
                    tD("notSet")
                  }
                />
                <ConfigBadge
                  icon={Layers}
                  label={tD("labelSolution")}
                  value={
                    resolveSolutionTypeLabel(project.wizard_data.solution?.solutionType as string | undefined)
                  }
                />
                <ConfigBadge
                  icon={Bot}
                  label={tD("labelAgents")}
                  value={
                    project.wizard_data.agents?.length > 0
                      ? tD("countItem", { count: project.wizard_data.agents.length })
                      : tD("notSet")
                  }
                />
                <ConfigBadge
                  icon={Wrench}
                  label={tD("labelSkills")}
                  value={
                    project.wizard_data.skills?.length > 0
                      ? tD("countItem", { count: project.wizard_data.skills.length })
                      : tD("notSet")
                  }
                />
                <ConfigBadge
                  icon={GitBranch}
                  label={tD("labelPipelines")}
                  value={
                    project.wizard_data.pipelines?.length > 0
                      ? tD("countItem", { count: project.wizard_data.pipelines.length })
                      : tD("notSet")
                  }
                />
                <ConfigBadge
                  icon={Monitor}
                  label={tD("labelPlatform")}
                  value={
                    project.wizard_data.platform?.platformId
                      ? PLATFORM_LABELS[
                          project.wizard_data.platform.platformId as string
                        ] ??
                        (project.wizard_data.platform.platformId as string)
                      : tD("notSet")
                  }
                />
              </div>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">{tD("noWizardData")}</p>
            )}
          </div>
        )}

        {/* Linear 연동 프리플라이트 카드 */}
        {hasLinear && (
          <LinearPreflightCard
            projectId={projectId}
            status={linearStatus ?? null}
            isFetching={linearFetching}
            onRefresh={() => void refetchLinearStatus()}
          />
        )}

        {/* PM 피드백 카드 (wizard 프로젝트이고 PM이 배정된 경우) */}
        {project.pm_profile_id && project.prototype_session_id && (
          <PMFeedbackCard
            projectId={projectId}
            pmProfileId={project.pm_profile_id}
            sessionId={project.prototype_session_id}
          />
        )}

        {/* 위험 구역 */}
        <div className="mt-6 rounded-2xl border border-red-200 bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <h2 className="mb-1 text-base font-semibold text-red-700">{tD("dangerZoneTitle")}</h2>
          <p className="mb-5 text-xs text-[var(--text-muted)]">{tD("dangerZoneDesc")}</p>

          {/* 초기화 완료 메시지 */}
          {resetResult && (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <p className="font-medium">{tD("resetSuccess")}</p>
              {resetResult.new_license_key && (
                <p className="mt-1 text-xs">
                  {tD("licenseKeyLabel")}{" "}
                  <code className="font-mono text-emerald-900">{resetResult.new_license_key}</code>
                  <br />
                  {tD("resetKeyUpdateNote")}
                </p>
              )}
            </div>
          )}

          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1 rounded-xl border border-amber-200 bg-amber-50/50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{tD("resetTitle")}</p>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">{tD("resetDesc")}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setResetOpen(true)}
                  className="shrink-0 flex items-center gap-1.5 rounded-lg border border-amber-300 bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-50 transition-colors"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  {tD("resetBtn")}
                </button>
              </div>
            </div>
            <div className="flex-1 rounded-xl border border-red-200 bg-red-50/50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{tD("deleteTitle")}</p>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">{tD("deleteDesc")}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setDeleteOpen(true)}
                  className="shrink-0 flex items-center gap-1.5 rounded-lg border border-red-300 bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  {tD("deleteBtn")}
                </button>
              </div>
            </div>
          </div>
        </div>
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
      <ResetProjectDialog
        projectName={project.name}
        isOpen={resetOpen}
        isResetting={resetting}
        onCancel={() => setResetOpen(false)}
        onConfirm={() => void handleReset()}
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
    <div className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2">
      <Icon className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
      <div className="min-w-0">
        <p className="text-[10px] text-[var(--text-muted)]">{label}</p>
        <p className="truncate text-xs font-medium text-[var(--text-primary)]">{value}</p>
      </div>
    </div>
  );
}

/* -- Linear 연동 프리플라이트 카드 -- */

interface LinearPreflightCardProps {
  projectId: string;
  status: ProjectLinearStatus | null;
  isFetching: boolean;
  onRefresh: () => void;
  /** true 면 sub-card 스타일로 렌더 */
  compact?: boolean;
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
        <div className="mt-0.5 h-4 w-4 shrink-0 animate-pulse rounded-full bg-[var(--border-subtle)]" />
      ) : ok ? (
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
      ) : (
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
      )}
      <div>
        <p className="text-sm font-medium text-[var(--text-primary)]">{label}</p>
        {description && <p className="text-xs text-[var(--text-muted)]">{description}</p>}
      </div>
    </div>
  );
}

function LinearPreflightCard({ projectId, status, isFetching, onRefresh, compact = false }: LinearPreflightCardProps) {
  const t = useTranslations("projects.linear");
  const credentialsReady = status?.credentials_saved === true;

  return (
    <div
      className={
        compact
          ? "rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-5"
          : "mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
      }
    >
      <div className={compact ? "mb-3 flex items-center justify-between" : "mb-5 flex items-center justify-between"}>
        <div className="flex items-center gap-2">
          <Zap className={compact ? "h-3.5 w-3.5 text-[var(--text-secondary)]" : "h-4 w-4 text-[var(--text-secondary)]"} />
          <h2 className={compact ? "text-sm font-semibold text-[var(--text-primary)]" : "text-lg font-semibold text-[var(--text-primary)]"}>
            {t("cardTitle")} {compact && <span className="ml-1 text-[11px] font-normal text-[var(--text-muted)]">{t("compactNote")}</span>}
          </h2>
        </div>
        <button
          onClick={onRefresh}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-muted)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          {t("refreshBtn")}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CheckItem
          ok={status ? credentialsReady : null}
          label={t("credentialsSaved")}
          description={
            credentialsReady
              ? status?.team_id
                ? t("teamIdDesc", { teamId: status.team_id })
                : t("credentialsSavedDesc")
              : t("credentialsNotSavedDesc")
          }
        />
        {credentialsReady && status?.api_key_masked && (
          <CheckItem
            ok={true}
            label={t("apiKeyConfirmed")}
            description={status.api_key_masked}
          />
        )}
      </div>

      <div className="mt-6 flex items-center gap-3 border-t border-[var(--border-subtle)] pt-6">
        {credentialsReady ? (
          <a
            href={`/projects/${projectId}/ai-team`}
            className="flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-all hover:opacity-90"
          >
            <Zap className="h-4 w-4" />
            {t("startAiTeamBtn")}
          </a>
        ) : (
          <Link
            href="/delivery"
            className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            {t("newSolutionBtn")}
          </Link>
        )}
        <span className="text-xs text-[var(--text-muted)]">
          {credentialsReady
            ? t("savedNote")
            : t("notSavedNote")}
        </span>
      </div>
    </div>
  );
}
