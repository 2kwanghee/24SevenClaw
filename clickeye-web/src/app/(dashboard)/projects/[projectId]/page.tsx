"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  RotateCcw,
} from "lucide-react";

import { useQuery } from "@tanstack/react-query";

import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog";
import { ResetProjectDialog } from "@/components/projects/reset-project-dialog";
import { ProjectForm } from "@/components/projects/project-form";
import { PMFeedbackCard } from "@/components/projects/pm-feedback-card";
import {
  useDeleteProject,
  useProject,
  useUpdateProject,
} from "@/hooks/use-projects";
import { apiClient, ApiClientError, integrations, projectLinearCredentials, type ProjectLinearStatus } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import {
  IntegrationValidationBadge,
  type ValidationStatus,
} from "@/components/solutions/wizard/integration-validation-badge";
import {
  checkLinearInputs,
  checkNotionInputs,
  describeIntegrationError,
} from "@/lib/integration-validators";

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
  const [resetOpen, setResetOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetResult, setResetResult] = useState<{ new_license_key: string | null } | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [envDownloading, setEnvDownloading] = useState(false);
  const [envVars, setEnvVars] = useState<Record<string, string>>(() => {
    const stored = useSolutionWizardStore.getState().data.env.envVars;
    return { ...stored };
  });

  /* --------------------------------------------------------------
    Linear / Notion 라이브 검증 — projects/[projectId] ZIP 재다운로드 게이트
    위저드 store(envValidation)와 분리된 로컬 상태로 관리한다.
  -------------------------------------------------------------- */
  const skillIds = useMemo<string[]>(
    () => ((project?.wizard_data?.skills ?? []) as { id: string }[]).map((s) => s.id),
    [project?.wizard_data?.skills],
  );
  const hasLinear = skillIds.includes("linear");
  const hasNotion = skillIds.includes("notion");

  const [linearValidation, setLinearValidation] = useState<{ status: ValidationStatus; message: string }>({
    status: "idle",
    message: "",
  });
  const [notionValidation, setNotionValidation] = useState<{ status: ValidationStatus; message: string }>({
    status: "idle",
    message: "",
  });
  const linearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const notionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const triggerLinearValidation = useCallback(
    (apiKey: string, teamId: string) => {
      if (linearTimerRef.current) clearTimeout(linearTimerRef.current);
      if (!apiKey.trim() || !teamId.trim()) {
        setLinearValidation({ status: "idle", message: "" });
        return;
      }
      // 클라이언트 사전 검증: 한글/이모지/제어문자가 섞이면 fetch 자체가 실패하므로 차단.
      const check = checkLinearInputs(apiKey, teamId);
      if (!check.ok) {
        setLinearValidation({ status: "invalid", message: check.message });
        return;
      }
      setLinearValidation({ status: "loading", message: "검증 중..." });
      linearTimerRef.current = setTimeout(async () => {
        if (!token) return;
        try {
          const res = await integrations.validateLinear(token, { api_key: apiKey, team_id: teamId });
          setLinearValidation({
            status: res.valid ? "valid" : "invalid",
            message: res.message,
          });
        } catch (err) {
          setLinearValidation({ status: "invalid", message: describeIntegrationError(err) });
        }
      }, 800);
    },
    [token],
  );

  const triggerNotionValidation = useCallback(
    (apiKey: string, databaseId: string) => {
      if (notionTimerRef.current) clearTimeout(notionTimerRef.current);
      if (!apiKey.trim() || !databaseId.trim()) {
        setNotionValidation({ status: "idle", message: "" });
        return;
      }
      const check = checkNotionInputs(apiKey, databaseId);
      if (!check.ok) {
        setNotionValidation({ status: "invalid", message: check.message });
        return;
      }
      setNotionValidation({ status: "loading", message: "검증 중..." });
      notionTimerRef.current = setTimeout(async () => {
        if (!token) return;
        try {
          const res = await integrations.validateNotion(token, { api_key: apiKey, database_id: databaseId });
          setNotionValidation({
            status: res.valid ? "valid" : "invalid",
            message: res.message,
          });
        } catch (err) {
          setNotionValidation({ status: "invalid", message: describeIntegrationError(err) });
        }
      }, 800);
    },
    [token],
  );

  useEffect(() => {
    if (!hasLinear) return;
    triggerLinearValidation(envVars["LINEAR_API_KEY"] ?? "", envVars["LINEAR_TEAM_ID"] ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [envVars["LINEAR_API_KEY"], envVars["LINEAR_TEAM_ID"], hasLinear]);

  useEffect(() => {
    if (!hasNotion) return;
    triggerNotionValidation(envVars["NOTION_API_KEY"] ?? "", envVars["NOTION_DATABASE_ID"] ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [envVars["NOTION_API_KEY"], envVars["NOTION_DATABASE_ID"], hasNotion]);

  const { data: linearStatus, refetch: refetchLinearStatus, isFetching: linearFetching } = useQuery({
    queryKey: ["linear-connection-status", projectId],
    queryFn: () => projectLinearCredentials.status(token, projectId),
    enabled: !!token && !!projectId,
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

  const handleDownloadEnv = useCallback(async () => {
    if (!token || !projectId) return;
    setEnvDownloading(true);
    try {
      const blob = await apiClient.projects.downloadEnv(token, projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = ".env";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // 실패 시 재다운로드 경로 유도
    } finally {
      setEnvDownloading(false);
    }
  }, [token, projectId]);

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
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
        <p className="mt-4 text-sm text-[var(--text-muted)]">불러오는 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">
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
  const isStale =
    project.anthropic_key_status === "stale" || project.linear_key_status === "stale";

  return (
    <div>
      {/* 브레드크럼 */}
      <div className="mb-8">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          프로젝트 목록
        </Link>
      </div>

      {/* Stale 키 갱신 배너 */}
      {isStale && (
        <div className="mb-6 flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-600" />
            <div>
              <p className="text-sm font-medium text-amber-800">API 키가 변경되었습니다</p>
              <p className="mt-0.5 text-xs text-amber-700">
                로컬 .env 파일을 갱신해야 새 키가 적용됩니다.{" "}
                {project.anthropic_key_status === "stale" && "Anthropic "}
                {project.linear_key_status === "stale" && "Linear "}
                키가 오래됐습니다.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 pl-7 sm:pl-0">
            <button
              onClick={handleDownloadEnv}
              disabled={envDownloading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100 transition-colors disabled:opacity-50"
            >
              {envDownloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
              .env 다운로드
            </button>
            <button
              onClick={handleRedownload}
              disabled={downloading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700 transition-colors disabled:opacity-50"
            >
              {downloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              ZIP 재다운로드
            </button>
          </div>
        </div>
      )}

      {isEditing ? (
        /* 수정 모드 */
        <div className="mx-auto max-w-lg rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">

          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">프로젝트 수정</h2>
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
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-[var(--text-primary)]">{project.name}</h1>
                <span
                  className={`rounded-md px-2.5 py-0.5 text-xs font-medium ${
                    isActive
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-zinc-100 text-zinc-500"
                  }`}
                >
                  {isActive ? "활성" : "보관됨"}
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
                수정
              </button>
              <Link
                href={`/projects/${projectId}/dashboard`}
                className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <BarChart3 className="h-3.5 w-3.5" />
                대시보드
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
                설정
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
              생성일: {formattedDate}
            </div>
            <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
              <Activity className="h-4 w-4" />
              상태: {isActive ? "활성" : "보관됨"}
            </div>
          </div>
        </div>

        {/* 설정 요약 + ZIP 다운로드 (wizard 프로젝트) */}
        {(project.wizard_data || project.project_type === "wizard") && (
          <div className="mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
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
              <p className="text-sm text-[var(--text-muted)]">
                위저드 설정 정보가 없습니다. ZIP을 다시 생성하려면 솔루션 위저드를 다시 진행해 주세요.
              </p>
            )}

            {/* ZIP 재다운로드 — API 키 입력 + 다운로드 */}
            {project.wizard_data && (() => {
              const wd = project.wizard_data as unknown as Record<string, unknown>;

              // authMethod: 위저드 env.authMethod 또는 solution.authMethod (이전 경로) 확인
              const authMethod: string =
                ((wd.env as Record<string, unknown>)?.authMethod as string) ||
                (project.wizard_data.solution?.authMethod as string) ||
                "api_key";
              const isOAuth = authMethod === "oauth_browser";

              const ENV_FIELDS: { key: string; label: string; placeholder: string }[] = [
                ...(!isOAuth
                  ? [{ key: "ANTHROPIC_API_KEY", label: "Anthropic API Key", placeholder: "sk-ant-..." }]
                  : []),
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

              // 모든 표시된 환경변수 필드가 채워졌는지 + 라이브 검증 결과 확인 — ZIP 다운로드 게이트
              const missingEnvKeys = ENV_FIELDS.filter(
                ({ key }) => !envVars[key]?.trim(),
              );
              const linearInvalid = hasLinear && linearValidation.status === "invalid";
              const notionInvalid = hasNotion && notionValidation.status === "invalid";
              const downloadDisabled =
                downloading ||
                missingEnvKeys.length > 0 ||
                linearInvalid ||
                notionInvalid;

              return (
                <div className="mt-6 border-t border-[var(--border-subtle)] pt-6 space-y-4">
                  {isOAuth ? (
                    <p className="text-xs text-[var(--text-muted)]">
                      {"OAuth 브라우저 인증 모드입니다. bash start.sh 실행 시 claude login이 자동으로 진행됩니다."}
                    </p>
                  ) : (
                    <p className="text-xs text-[var(--text-muted)]">
                      API 키는 서버에 저장되지 않습니다. ZIP의 <code className="text-[var(--text-secondary)]">.env</code>에 직접 작성됩니다.
                    </p>
                  )}
                  {hasLinear && (
                    <LinearPreflightCard
                      compact
                      projectId={projectId}
                      status={linearStatus ?? null}
                      isFetching={linearFetching}
                      onRefresh={() => void refetchLinearStatus()}
                    />
                  )}
                  {ENV_FIELDS.length > 0 && (
                    <div className="grid gap-2 sm:grid-cols-2">
                      {ENV_FIELDS.map(({ key, label, placeholder }) => {
                        const isEmpty = !envVars[key]?.trim();
                        return (
                          <div key={key}>
                            <label className="mb-1 block text-[11px] font-medium text-[var(--text-muted)]">
                              {label}
                              {isEmpty && (
                                <span className="ml-1 text-red-600">*</span>
                              )}
                            </label>
                            <input
                              type="text"
                              value={envVars[key] ?? ""}
                              onChange={(e) =>
                                setEnvVars((prev) => ({ ...prev, [key]: e.target.value }))
                              }
                              placeholder={placeholder}
                              aria-invalid={isEmpty}
                              className={`w-full rounded-lg border bg-[var(--bg-surface)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-1 ${
                                isEmpty
                                  ? "border-red-300 focus:border-red-400 focus:ring-red-200"
                                  : "border-[var(--border-subtle)] focus:border-zinc-400 focus:ring-zinc-200"
                              }`}
                            />
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {missingEnvKeys.length > 0 && (
                    <div
                      role="alert"
                      className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2"
                    >
                      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                      <p className="text-xs text-amber-700">
                        필수 환경변수 {missingEnvKeys.length}개(
                        {missingEnvKeys.map((f) => f.label).join(", ")})를 입력해야
                        ZIP을 다운로드할 수 있습니다.
                      </p>
                    </div>
                  )}
                  {(hasLinear || hasNotion) && (
                    <div className="space-y-2">
                      {hasLinear && (
                        <IntegrationValidationBadge
                          name="Linear"
                          status={linearValidation.status}
                          message={linearValidation.message}
                        />
                      )}
                      {hasNotion && (
                        <IntegrationValidationBadge
                          name="Notion"
                          status={notionValidation.status}
                          message={notionValidation.message}
                        />
                      )}
                    </div>
                  )}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleRedownload}
                      disabled={downloadDisabled}
                      className="flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
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
                    <span className="text-xs text-[var(--text-muted)]">
                      {missingEnvKeys.length > 0
                        ? "환경변수 입력 후 다운로드할 수 있습니다"
                        : "저장된 설정 + 입력한 API 키로 ZIP을 생성합니다"}
                    </span>
                  </div>
                  {downloadError && (
                    <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                      <AlertCircle className="h-3.5 w-3.5 text-red-600" />
                      <p className="text-xs text-red-700">{downloadError}</p>
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

        {/* Linear 연동 프리플라이트 카드는 ZIP 다운로드 카드 안으로 통합 (아래 IIFE 내부) */}

        {/* 위험 구역 */}
        <div className="mt-6 rounded-2xl border border-red-200 bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <h2 className="mb-1 text-base font-semibold text-red-700">위험 구역</h2>
          <p className="mb-5 text-xs text-[var(--text-muted)]">
            아래 작업은 되돌릴 수 없습니다. 신중하게 진행하세요.
          </p>

          {/* 초기화 완료 메시지 */}
          {resetResult && (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              <p className="font-medium">프로젝트가 초기화되었습니다.</p>
              {resetResult.new_license_key && (
                <p className="mt-1 text-xs">
                  새 라이선스 키:{" "}
                  <code className="font-mono text-emerald-900">{resetResult.new_license_key}</code>
                  <br />
                  로컬 .env 파일의 <code>LICENSE_KEY</code>를 위 값으로 업데이트하세요.
                </p>
              )}
            </div>
          )}

          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1 rounded-xl border border-amber-200 bg-amber-50/50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">프로젝트 초기화</p>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                    위자드 설정, 티켓, 산출물, 세션 등 진행 데이터를 삭제합니다.
                    프로젝트 ID와 이름은 유지됩니다.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setResetOpen(true)}
                  className="shrink-0 flex items-center gap-1.5 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-50 transition-colors"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  초기화
                </button>
              </div>
            </div>
            <div className="flex-1 rounded-xl border border-red-200 bg-red-50/50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">프로젝트 삭제</p>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                    프로젝트와 모든 연관 데이터를 완전히 삭제합니다.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setDeleteOpen(true)}
                  className="shrink-0 flex items-center gap-1.5 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  삭제
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
      <Icon className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
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
  /** true 면 ZIP 다운로드 카드 안에 임베드되는 sub-card 스타일로 렌더 */
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
        <div className="mt-0.5 h-4 w-4 shrink-0 animate-pulse rounded-full bg-zinc-200" />
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
  const credentialsReady = status?.credentials_saved === true;

  return (
    <div
      className={
        compact
          ? "rounded-xl border border-[var(--border-subtle)] bg-zinc-50 p-5"
          : "mt-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
      }
    >
      <div className={compact ? "mb-3 flex items-center justify-between" : "mb-5 flex items-center justify-between"}>
        <div className="flex items-center gap-2">
          <Zap className={compact ? "h-3.5 w-3.5 text-zinc-700" : "h-4 w-4 text-zinc-700"} />
          <h2 className={compact ? "text-sm font-semibold text-[var(--text-primary)]" : "text-lg font-semibold text-[var(--text-primary)]"}>
            Linear 연동 상태 {compact && <span className="ml-1 text-[11px] font-normal text-[var(--text-muted)]">(서버 자동화용)</span>}
          </h2>
        </div>
        <button
          onClick={onRefresh}
          disabled={isFetching}
          className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-muted)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          새로고침
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CheckItem
          ok={status ? credentialsReady : null}
          label="자격증명 저장됨"
          description={
            credentialsReady
              ? status?.team_id
                ? `팀 ID: ${status.team_id}`
                : "Linear API 키가 등록되어 있습니다"
              : "프로젝트 생성 시 Linear API 키와 팀 ID를 입력하면 자동 저장됩니다"
          }
        />
        {credentialsReady && status?.api_key_masked && (
          <CheckItem
            ok={true}
            label="API 키 확인됨"
            description={status.api_key_masked}
          />
        )}
      </div>

      <div className="mt-6 flex items-center gap-3 border-t border-[var(--border-subtle)] pt-6">
        {credentialsReady ? (
          <a
            href={`/projects/${projectId}/ai-team`}
            className="flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-zinc-800"
          >
            <Zap className="h-4 w-4" />
            AI Team 시작하기
          </a>
        ) : (
          <a
            href="/solutions/new"
            className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            새 솔루션 만들기
          </a>
        )}
        <span className="text-xs text-[var(--text-muted)]">
          {credentialsReady
            ? "Linear 자격증명이 이 프로젝트에 저장되어 있습니다."
            : "프로젝트 생성 위저드에서 Linear API 키를 입력하면 프로젝트에 종속 저장됩니다."}
        </span>
      </div>
    </div>
  );
}
