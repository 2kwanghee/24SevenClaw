"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  Plus,
  RefreshCcw,
  RotateCcw,
  Loader2,
  AlertTriangle,
  User,
  Bot,
  Brain,
  FileText,
  CheckCircle2,
  Sparkles,
  Link2,
  Trash2,
  X,
  Terminal,
} from "lucide-react";

import { PipelineStepper } from "@/components/ai-team/pipeline-stepper";
import { ReviewDiffViewer } from "@/components/ai-team/review-diff-viewer";
import { SessionCreateModal } from "@/components/ai-team/session-create-modal";
import { SubTaskCard } from "@/components/ai-team/subtask-card";
import {
  useSessionList,
  useSessionSummary,
  useReviewRounds,
  useTransition,
  useGenerateDrafts,
  usePushToLinear,
  useDeleteSession,
  useResumePipeline,
  useSyncLinearStates,
  useLinearTeamStates,
} from "@/hooks/use-orchestrator";
import { useProject } from "@/hooks/use-projects";
import type { LinearSyncHint, PushToLinearResponse } from "@/lib/api-client";
import type { OrchestratorPhase } from "@/lib/api-client";

export default function AITeamDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const tPhase = useTranslations("delivery.phase");
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");
  const [modalOpen, setModalOpen] = useState(false);
  const [linearHint, setLinearHint] = useState<LinearSyncHint | null>(null);
  const [linearPushResult, setLinearPushResult] = useState<PushToLinearResponse | null>(null);
  const [linearPushError, setLinearPushError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  const { data: projectData, refetch: refetchProject } = useProject(projectId);
  const bootstrapStatus = projectData?.bootstrap_status ?? "skipped";

  const {
    data: sessions,
    isLoading: sessionsLoading,
    refetch: refetchSessions,
  } = useSessionList(projectId);

  const {
    data: summary,
    isLoading: summaryLoading,
    refetch: refetchSummary,
  } = useSessionSummary(selectedSessionId);

  // 부트스트랩 세션(pending_review)은 "reviewing"이어도 수동 검토가 필요 — 자동 진행 아님
  const isBootstrapReviewing =
    bootstrapStatus === "pending_review" && summary?.session?.phase === "reviewing";
  const isAutoProgressPhase =
    !isBootstrapReviewing &&
    ["drafting", "reviewing", "integrating", "approved", "transitioning"].includes(
      summary?.session?.phase ?? "",
    );

  const { data: reviewData } = useReviewRounds(selectedSessionId, isAutoProgressPhase);

  const transition = useTransition();
  const generateDrafts = useGenerateDrafts();
  const pushToLinear = usePushToLinear();
  const deleteSession = useDeleteSession(projectId);
  const resumePipeline = useResumePipeline();
  const syncLinearStates = useSyncLinearStates(selectedSessionId);
  const { data: teamStates } = useLinearTeamStates(selectedSessionId);

  const firstSessionId = sessions?.items[0]?.id ?? "";
  const activeSessionId = selectedSessionId || firstSessionId;

  useEffect(() => {
    if (!selectedSessionId && firstSessionId) {
      setSelectedSessionId(firstSessionId);
    }
  }, [selectedSessionId, firstSessionId]);

  // 세션 진입 시 Linear 상태 자동 동기화 (1회)
  useEffect(() => {
    if (!selectedSessionId) return;
    const hasLinearIssues = summary?.subtasks?.some((st) => !!st.linear_issue_id);
    if (hasLinearIssues && !syncLinearStates.isPending) {
      syncLinearStates.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSessionId, !!summary]);

  // Linear 상태 주기 동기화 — DB 폴링은 stale일 수 있으므로 별도 간격으로 sync 실행
  useEffect(() => {
    if (!selectedSessionId) return;
    const hasLinearIssues = summary?.subtasks?.some((st) => !!st.linear_issue_id);
    if (!hasLinearIssues) return;

    const intervalMs = isAutoProgressPhase ? 10_000 : 30_000;
    const timer = setInterval(() => {
      if (!syncLinearStates.isPending) {
        syncLinearStates.mutate();
      }
    }, intervalMs);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSessionId, !!summary, isAutoProgressPhase, summary?.subtasks?.length]);

  const session = summary?.session;
  const subtasks = summary?.subtasks ?? [];
  const phaseHistory = summary?.phase_history ?? [];
  const reviewRounds = reviewData?.items ?? [];

  // 부트스트랩 running 상태일 때 10초마다 프로젝트 재조회
  useEffect(() => {
    if (bootstrapStatus !== "running") return;
    const timer = setInterval(() => {
      void refetchProject();
    }, 10_000);
    return () => clearInterval(timer);
  }, [bootstrapStatus, refetchProject]);

  // 부트스트랩 완료 시 세션 목록 자동 갱신
  useEffect(() => {
    if (bootstrapStatus === "completed") {
      void refetchSessions();
    }
  }, [bootstrapStatus, refetchSessions]);

  const handleRefresh = () => {
    void refetchProject();
    refetchSessions();
    refetchSummary();
    if (
      selectedSessionId &&
      !syncLinearStates.isPending &&
      summary?.subtasks?.some((st) => !!st.linear_issue_id)
    ) {
      syncLinearStates.mutate();
    }
  };

  const handleDeleteConfirm = () => {
    if (!deleteTarget) return;
    deleteSession.mutate(deleteTarget.id, {
      onSuccess: () => {
        if (selectedSessionId === deleteTarget.id) {
          setSelectedSessionId("");
          setLinearHint(null);
          setLinearPushResult(null);
          setLinearPushError(null);
        }
        setDeleteTarget(null);
      },
    });
  };

  const handleApprove = () => {
    if (!session) return;
    transition.mutate({
      sessionId: session.id,
      targetPhase: "approved" as OrchestratorPhase,
      message: "사용자 승인",
    });
  };

  const isReviewPhase = session?.phase === "reviewing";

  const handleResume = () => {
    if (!session) return;
    resumePipeline.mutate({ sessionId: session.id });
  };

  const handleGenerateDrafts = () => {
    if (!session) return;
    setLinearPushResult(null);
    setLinearPushError(null);
    generateDrafts.mutate(
      { sessionId: session.id },
      {
        onSuccess: (data) => {
          setLinearHint(data.linear_sync_hint);
          void refetchSummary();
        },
      },
    );
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}`}
            className="rounded-lg p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            aria-label="프로젝트로 돌아가기"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-[var(--text-primary)]">AI Team 운영</h1>
            <p className="text-xs text-[var(--text-muted)]">
              3계층 오케스트레이션 대시보드
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={summaryLoading}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)] disabled:opacity-50"
            aria-label="새로고침"
          >
            <RefreshCcw
              className={`h-3 w-3 ${summaryLoading ? "animate-spin" : ""}`}
            />
            새로고침
          </button>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90"
          >
            <Plus className="h-3 w-3" />
            새 작업 요청
          </button>
        </div>
      </div>

      {/* 부트스트랩 배너 */}
      {bootstrapStatus === "pending" && (
        <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300">
          <Terminal className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            셋업 대기 중 — 딜리버리 환경이 준비되면 요구사항이 자동으로 등록됩니다.
          </span>
        </div>
      )}
      {bootstrapStatus === "running" && (
        <div className="flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
          <span>요구사항 분석 및 Linear 이슈 등록 진행 중입니다…</span>
        </div>
      )}
      {bootstrapStatus === "pending_review" && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            분해된 서브태스크를 검토하고 각 카드를 <strong>승인</strong>하세요.
            승인하면 Linear에 이슈가 <strong>자동으로 등록</strong>됩니다.
          </span>
        </div>
      )}
      {bootstrapStatus === "failed" && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            자동 등록 중 오류가 발생했습니다. 재시도하려면 로컬 터미널에서{" "}
            <code className="rounded bg-red-100 px-1 py-0.5 font-mono text-xs dark:bg-red-900">
              bash scripts/bootstrap_clickeye.sh
            </code>
            을 실행하세요.
          </span>
        </div>
      )}

      {/* 세션 선택 탭 */}
      {sessions && sessions.items.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {sessions.items.map((s) => (
            <div key={s.id} className="group relative flex shrink-0 items-center">
              <button
                type="button"
                onClick={() => setSelectedSessionId(s.id)}
                className={`rounded-lg py-1.5 pl-3 pr-2 text-xs font-medium transition-colors ${
                  s.id === activeSessionId
                    ? "bg-[var(--accent)] text-[var(--accent-fg)] shadow-sm"
                    : "text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                }`}
              >
                {s.title}
                <span className="ml-1.5 rounded bg-[var(--bg-hover)] px-1 py-0.5 text-[10px] text-[var(--text-muted)]">
                  {tPhase.has(s.phase) ? tPhase(s.phase) : s.phase}
                </span>
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setDeleteTarget({ id: s.id, title: s.title });
                }}
                className="ml-0.5 rounded p-0.5 text-[var(--text-muted)] opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                aria-label={`${s.title} 삭제`}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 로딩 */}
      {(sessionsLoading || (summaryLoading && !summary)) && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" />
        </div>
      )}

      {/* 세션 없음 */}
      {sessions && sessions.items.length === 0 && !sessionsLoading && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--bg-hover)]">
            <Bot className="h-7 w-7 text-[var(--text-muted)]" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            아직 생성된 작업이 없습니다
          </p>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            첫 작업 요청하기
          </button>
        </div>
      )}

      {/* 3계층 대시보드 */}
      {session && (
        <div className="space-y-6">
          {/* --- 1계층: 사람 (Human) --- */}
          <section
            className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
            aria-label="사람 계층"
          >
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-amber-50">
                <User className="h-3.5 w-3.5 text-amber-600" />
              </div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">사람</h2>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* 프로젝트 단계 배지 */}
              <div className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2">
                <span className="text-xs text-[var(--text-muted)]">현재 단계</span>
                <span className="rounded-md bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700">
                  {tPhase.has(session.phase) ? tPhase(session.phase) : session.phase}
                </span>
              </div>

              {/* 리스크 플래그 */}
              {session.risk_flags.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                  {session.risk_flags.map((flag) => (
                    <span
                      key={flag}
                      className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              )}

              {/* AI 초안 생성 버튼 (assigned 단계일 때) */}
              {session.phase === "assigned" && (
                <button
                  type="button"
                  onClick={handleGenerateDrafts}
                  disabled={generateDrafts.isPending}
                  className="ml-auto flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-4 py-2 text-xs font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90 disabled:opacity-50"
                >
                  {generateDrafts.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  AI 초안 생성
                </button>
              )}

              {/* 부트스트랩 수동 검토 안내 (pending_review + reviewing) */}
              {isBootstrapReviewing && (
                <div className="ml-auto flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5">
                  <CheckCircle2 className="h-3 w-3 text-amber-600" />
                  <span className="text-xs text-amber-700">각 카드를 승인하면 Linear에 자동 등록됩니다</span>
                </div>
              )}

              {/* 자동 진행 중 표시 (drafting/reviewing/integrating) */}
              {isAutoProgressPhase && (
                <div className="ml-auto flex items-center gap-1.5 rounded-lg border border-violet-200 bg-violet-50 px-3 py-1.5">
                  <Loader2 className="h-3 w-3 animate-spin text-violet-600" />
                  <span className="text-xs text-violet-700">자동 진행 중…</span>
                  <button
                    type="button"
                    onClick={handleResume}
                    disabled={resumePipeline.isPending}
                    title="파이프라인이 멈춘 경우 재개"
                    className="ml-1 flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-violet-600 hover:bg-violet-100 disabled:opacity-50"
                  >
                    <RotateCcw className="h-3 w-3" />
                    재개
                  </button>
                </div>
              )}

              {/* 승인 버튼 (validating 단계일 때) */}
              {session.phase === "validating" && (
                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={transition.isPending}
                  className="ml-auto flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-4 py-2 text-xs font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90 disabled:opacity-50"
                >
                  {transition.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  )}
                  승인
                </button>
              )}
            </div>

            {/* 단계 이력 간략 표시 */}
            {phaseHistory.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {phaseHistory.slice(-5).map((evt) => (
                  <span
                    key={evt.id}
                    className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] text-[var(--text-muted)]"
                  >
                    {tPhase.has(evt.new_phase) ? tPhase(evt.new_phase) : evt.new_phase}
                    {evt.message ? ` — ${evt.message}` : ""}
                  </span>
                ))}
              </div>
            )}
          </section>

          {/* --- 2계층: PM AI --- */}
          <section aria-label="PM AI 계층" className="space-y-4">
            <div className="flex items-center gap-2 px-1">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-50">
                <Brain className="h-3.5 w-3.5 text-violet-600" />
              </div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">PM AI</h2>
            </div>

            {/* 10단계 파이프라인 스테퍼 */}
            <PipelineStepper currentPhase={session.phase} />

            {/* prompt_template 뷰어 */}
            {session.prompt_template && (
              <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                <div className="mb-3 flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    프롬프트 템플릿
                  </h3>
                </div>
                <pre className="max-h-40 overflow-auto rounded-lg bg-[var(--bg-hover)] p-3 text-xs text-[var(--text-secondary)] whitespace-pre-wrap">
                  {session.prompt_template}
                </pre>
              </div>
            )}

            {/* 리스크 칩 */}
            {session.risk_flags.length > 0 && (
              <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                <h3 className="mb-2 text-xs font-semibold text-[var(--text-muted)]">
                  감지된 리스크
                </h3>
                <div className="flex flex-wrap gap-2">
                  {session.risk_flags.map((flag) => (
                    <span
                      key={flag}
                      className="flex items-center gap-1 rounded-lg bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
                    >
                      <AlertTriangle className="h-3 w-3" />
                      {flag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 초안/리뷰 (drafting 이상 단계일 때) */}
            {["drafting", "reviewing", "integrating", "validating", "approved", "transitioning", "completed"].includes(session.phase) && reviewRounds.length > 0 && (
              <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">
                  {isReviewPhase ? "리뷰 라운드" : "AI 초안"}
                </h3>
                <div className="space-y-3">
                  {reviewRounds.map((round) => (
                    <ReviewDiffViewer key={round.id} round={round} />
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* 로컬 파이프라인 안내 (approved 이후) */}
          {["approved", "transitioning", "completed"].includes(session.phase) && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
              <div className="mb-2 flex items-center gap-2">
                <Terminal className="h-4 w-4 text-emerald-700" />
                <h3 className="text-sm font-semibold text-emerald-800">
                  코드 작성은 로컬 파이프라인에서 실행됩니다
                </h3>
              </div>
              <p className="text-xs text-emerald-700">
                각 태스크 카드의 <strong>큐 등록</strong> 버튼을 눌러 검수를 완료하세요.
                Linear 이슈가 <strong>Todo</strong> 상태로 이동하면 로컬 PC의 파이프라인이
                자동으로 Claude에게 코드 작성을 지시합니다.
              </p>
              <p className="mt-1.5 text-[11px] text-emerald-600">
                파이프라인이 실행 중이 아니라면 딜리버리 파이프라인을 먼저 시작하세요.
              </p>
            </div>
          )}

          {/* Linear 동기화 힌트 */}
          {linearHint && (
            <div className="rounded-2xl border border-violet-200 bg-violet-50 p-5">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Link2 className="h-4 w-4 text-violet-600" />
                  <h3 className="text-sm font-semibold text-violet-700">
                    Linear 동기화
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setLinearHint(null)}
                  className="rounded px-2 py-0.5 text-[11px] text-[var(--text-muted)] hover:bg-violet-100 hover:text-[var(--text-secondary)]"
                >
                  닫기
                </button>
              </div>
              <p className="mb-3 text-xs text-[var(--text-secondary)]">{linearHint.instructions}</p>
              {linearHint.session_description && (
                <div className="mb-3 rounded-lg border border-violet-200 bg-[var(--bg-surface)] px-3 py-2">
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-violet-700">
                    원본 요구사항
                  </p>
                  <p className="whitespace-pre-wrap text-[11px] text-[var(--text-secondary)]">
                    {linearHint.session_description}
                  </p>
                </div>
              )}
              <div className="space-y-2">
                {linearHint.subtasks.map((st) => (
                  <div
                    key={st.title}
                    className="rounded-lg border border-violet-200 bg-[var(--bg-surface)] px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-violet-50 px-1.5 py-0.5 text-[10px] font-medium text-violet-700">
                        {st.role}
                      </span>
                      <span className="text-xs font-medium text-[var(--text-primary)]">
                        {st.title}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-[var(--text-muted)]">
                      {st.draft_summary}
                    </p>
                  </div>
                ))}
              </div>
              {/* push-to-linear 결과 */}
              {linearPushResult && (
                <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
                  <p className="text-xs text-emerald-700">
                    ✓ Linear 이슈 생성 완료: {linearPushResult.created_identifiers.join(", ")}
                  </p>
                </div>
              )}
              {linearPushError && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
                  <p className="text-xs text-amber-700">
                    {linearPushError.includes("자격증명") ? (
                      <>
                        Linear 자격증명이 없습니다.{" "}
                        <a href="/settings/linear" className="underline hover:text-amber-900">
                          설정에서 API 키를 저장하세요 →
                        </a>
                      </>
                    ) : (
                      linearPushError
                    )}
                  </p>
                </div>
              )}
              {!linearPushResult && !linearPushError && (
                <p className="mt-3 text-[11px] text-[var(--text-muted)]">
                  로컬 Claude Code에서 linear 스킬의 sync 명령을 실행하면 위 이슈가 자동으로 생성됩니다.
                </p>
              )}
            </div>
          )}

          {/* --- 3계층: AI Team --- */}
          <section
            className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
            aria-label="AI Team 계층"
          >
            {(() => {
              const approvedCount = subtasks.filter((s) => s.status === "approved").length;
              const dependencyMap = new Map(subtasks.map((s) => [s.title, s]));
              const sortedByOrder = [...subtasks].sort((a, b) => a.order_index - b.order_index);
              const nextRecommended = sortedByOrder.find(
                (s) =>
                  s.status !== "approved" &&
                  s.depends_on.every((t) => dependencyMap.get(t)?.status === "approved"),
              );
              const nextRecommendedId = nextRecommended?.id ?? null;

              return (
                <>
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--bg-hover)]">
                        <Bot className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
                      </div>
                      <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                        AI Team
                      </h2>
                      <span className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] text-[var(--text-muted)]">
                        {subtasks.length}개 태스크
                      </span>
                      {subtasks.length > 0 && (
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                          approvedCount === subtasks.length
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-violet-50 text-violet-700"
                        }`}>
                          {approvedCount} / {subtasks.length} 승인 완료
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)]">
                      {isAutoProgressPhase ? "Linear 10초 동기화" : "Linear 30초 동기화"}
                    </span>
                  </div>

                  {subtasks.length === 0 ? (
                    <p className="py-8 text-center text-sm text-[var(--text-muted)]">
                      아직 서브태스크가 없습니다
                    </p>
                  ) : (
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {sortedByOrder.map((st, idx) => (
                        <SubTaskCard
                          key={st.id}
                          subtask={st}
                          sessionId={selectedSessionId}
                          teamStates={teamStates ?? []}
                          orderNum={idx + 1}
                          total={subtasks.length}
                          dependencyMap={dependencyMap}
                          isNextRecommended={st.id === nextRecommendedId}
                        />
                      ))}
                    </div>
                  )}
                </>
              );
            })()}
          </section>
        </div>
      )}

      {/* 세션 생성 모달 */}
      <SessionCreateModal
        projectId={projectId}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={(id) => setSelectedSessionId(id)}
      />

      {/* 세션 삭제 확인 다이얼로그 */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setDeleteTarget(null)}
          />
          <div className="relative w-full max-w-sm rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-2xl">
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50">
                <Trash2 className="h-4 w-4 text-red-600" />
              </div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                작업 요청 삭제
              </h2>
            </div>

            <p className="mb-2 text-sm text-[var(--text-secondary)]">
              <span className="font-medium text-[var(--text-primary)]">
                &ldquo;{deleteTarget.title}&rdquo;
              </span>{" "}
              을(를) 삭제하시겠습니까?
            </p>
            <p className="mb-1 text-xs text-[var(--text-muted)]">
              서브태스크·리뷰 데이터가 모두 삭제됩니다.
            </p>
            <p className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              ⚠ Linear에 등록된 이슈는 삭제되지 않습니다. Linear에서 직접
              취소 또는 삭제해 주세요.
            </p>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                disabled={deleteSession.isPending}
                className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] disabled:opacity-50"
              >
                취소
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={deleteSession.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-red-500 disabled:opacity-50"
              >
                {deleteSession.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Trash2 className="h-3 w-3" />
                )}
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
