"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Plus,
  RefreshCcw,
  Loader2,
  AlertTriangle,
  User,
  Bot,
  Brain,
  FileText,
  CheckCircle2,
  Sparkles,
  Link2,
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
} from "@/hooks/use-orchestrator";
import type { LinearSyncHint, PushToLinearResponse } from "@/lib/api-client";
import type { OrchestratorPhase } from "@/lib/api-client";

const PHASE_LABELS: Record<string, string> = {
  requested: "요청됨",
  decomposed: "분해됨",
  assigned: "배정됨",
  drafting: "초안 작성",
  reviewing: "리뷰 중",
  integrating: "통합 중",
  validating: "검증 중",
  approved: "승인됨",
  transitioning: "전환 중",
  completed: "완료",
};

export default function AITeamDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");
  const [modalOpen, setModalOpen] = useState(false);
  const [linearHint, setLinearHint] = useState<LinearSyncHint | null>(null);
  const [linearPushResult, setLinearPushResult] = useState<PushToLinearResponse | null>(null);
  const [linearPushError, setLinearPushError] = useState<string | null>(null);

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

  const { data: reviewData } = useReviewRounds(selectedSessionId);

  const transition = useTransition();
  const generateDrafts = useGenerateDrafts();
  const pushToLinear = usePushToLinear();

  // 세션이 로드되면 첫 세션 자동 선택
  const activeSessionId = selectedSessionId || sessions?.items[0]?.id || "";
  if (!selectedSessionId && sessions?.items[0]?.id) {
    setSelectedSessionId(sessions.items[0].id);
  }

  const session = summary?.session;
  const subtasks = summary?.subtasks ?? [];
  const phaseHistory = summary?.phase_history ?? [];
  const reviewRounds = reviewData?.items ?? [];

  const handleRefresh = () => {
    refetchSessions();
    refetchSummary();
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
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200"
            aria-label="프로젝트로 돌아가기"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white">AI Team 운영</h1>
            <p className="text-xs text-slate-500">
              3계층 오케스트레이션 대시보드
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={summaryLoading}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200 disabled:opacity-50"
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
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-violet-500"
          >
            <Plus className="h-3 w-3" />
            새 작업 요청
          </button>
        </div>
      </div>

      {/* 세션 선택 탭 */}
      {sessions && sessions.items.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {sessions.items.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSelectedSessionId(s.id)}
              className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                s.id === activeSessionId
                  ? "bg-violet-500/10 text-violet-300 ring-1 ring-violet-500/30"
                  : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
              }`}
            >
              {s.title}
              <span className="ml-1.5 rounded bg-white/5 px-1 py-0.5 text-[10px] text-slate-500">
                {PHASE_LABELS[s.phase] ?? s.phase}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* 로딩 */}
      {(sessionsLoading || (summaryLoading && !summary)) && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-violet-400" />
        </div>
      )}

      {/* 세션 없음 */}
      {sessions && sessions.items.length === 0 && !sessionsLoading && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5">
            <Bot className="h-7 w-7 text-slate-600" />
          </div>
          <p className="text-sm text-slate-500">
            아직 생성된 작업이 없습니다
          </p>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500"
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
            className="rounded-2xl border border-white/5 bg-slate-900/50 p-6"
            aria-label="사람 계층"
          >
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-amber-500/10">
                <User className="h-3.5 w-3.5 text-amber-400" />
              </div>
              <h2 className="text-sm font-semibold text-slate-200">사람</h2>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* 프로젝트 단계 배지 */}
              <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2">
                <span className="text-xs text-slate-500">현재 단계</span>
                <span className="rounded-md bg-violet-500/10 px-2 py-0.5 text-xs font-medium text-violet-300">
                  {PHASE_LABELS[session.phase] ?? session.phase}
                </span>
              </div>

              {/* 리스크 플래그 */}
              {session.risk_flags.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                  {session.risk_flags.map((flag) => (
                    <span
                      key={flag}
                      className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-400"
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
                  className="ml-auto flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
                >
                  {generateDrafts.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  AI 초안 생성
                </button>
              )}

              {/* 승인 버튼 (validating 단계일 때) */}
              {session.phase === "validating" && (
                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={transition.isPending}
                  className="ml-auto flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
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
                    className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-500"
                  >
                    {PHASE_LABELS[evt.new_phase] ?? evt.new_phase}
                    {evt.message ? ` — ${evt.message}` : ""}
                  </span>
                ))}
              </div>
            )}
          </section>

          {/* --- 2계층: PM AI --- */}
          <section aria-label="PM AI 계층" className="space-y-4">
            <div className="flex items-center gap-2 px-1">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-violet-500/10">
                <Brain className="h-3.5 w-3.5 text-violet-400" />
              </div>
              <h2 className="text-sm font-semibold text-slate-200">PM AI</h2>
            </div>

            {/* 10단계 파이프라인 스테퍼 */}
            <PipelineStepper currentPhase={session.phase} />

            {/* prompt_template 뷰어 */}
            {session.prompt_template && (
              <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
                <div className="mb-3 flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-slate-400" />
                  <h3 className="text-sm font-semibold text-slate-200">
                    프롬프트 템플릿
                  </h3>
                </div>
                <pre className="max-h-40 overflow-auto rounded-lg bg-slate-950/50 p-3 text-xs text-slate-300 whitespace-pre-wrap">
                  {session.prompt_template}
                </pre>
              </div>
            )}

            {/* 리스크 칩 */}
            {session.risk_flags.length > 0 && (
              <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-4">
                <h3 className="mb-2 text-xs font-semibold text-slate-400">
                  감지된 리스크
                </h3>
                <div className="flex flex-wrap gap-2">
                  {session.risk_flags.map((flag) => (
                    <span
                      key={flag}
                      className="flex items-center gap-1 rounded-lg bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-400"
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
              <div className="rounded-2xl border border-white/5 bg-slate-900/50 p-6">
                <h3 className="mb-4 text-sm font-semibold text-slate-200">
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

          {/* Linear 동기화 힌트 */}
          {linearHint && (
            <div className="rounded-2xl border border-violet-500/20 bg-violet-500/5 p-5">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Link2 className="h-4 w-4 text-violet-400" />
                  <h3 className="text-sm font-semibold text-violet-300">
                    Linear 동기화
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setLinearHint(null)}
                  className="rounded px-2 py-0.5 text-[11px] text-slate-500 hover:bg-white/5 hover:text-slate-300"
                >
                  닫기
                </button>
              </div>
              <p className="mb-3 text-xs text-slate-400">{linearHint.instructions}</p>
              <div className="space-y-2">
                {linearHint.subtasks.map((st) => (
                  <div
                    key={st.title}
                    className="rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-violet-500/10 px-1.5 py-0.5 text-[10px] font-medium text-violet-400">
                        {st.role}
                      </span>
                      <span className="text-xs font-medium text-slate-200">
                        {st.title}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-slate-500">
                      {st.draft_summary}
                    </p>
                  </div>
                ))}
              </div>
              {/* push-to-linear 결과 */}
              {linearPushResult && (
                <div className="mt-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2">
                  <p className="text-xs text-emerald-300">
                    ✓ Linear 이슈 생성 완료: {linearPushResult.created_identifiers.join(", ")}
                  </p>
                </div>
              )}
              {linearPushError && (
                <div className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2">
                  <p className="text-xs text-amber-300">
                    {linearPushError.includes("자격증명") ? (
                      <>
                        Linear 자격증명이 없습니다.{" "}
                        <a href="/settings/linear" className="underline hover:text-amber-200">
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
                <p className="mt-3 text-[11px] text-slate-600">
                  로컬 Claude Code에서 linear 스킬의 sync 명령을 실행하면 위 이슈가 자동으로 생성됩니다.
                </p>
              )}
            </div>
          )}

          {/* --- 3계층: AI Team --- */}
          <section
            className="rounded-2xl border border-white/5 bg-slate-900/50 p-6"
            aria-label="AI Team 계층"
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-cyan-500/10">
                  <Bot className="h-3.5 w-3.5 text-cyan-400" />
                </div>
                <h2 className="text-sm font-semibold text-slate-200">
                  AI Team
                </h2>
                <span className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-500">
                  {subtasks.length}개 태스크
                </span>
              </div>
              <span className="text-[10px] text-slate-600">30초 자동 갱신</span>
            </div>

            {subtasks.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                아직 서브태스크가 없습니다
              </p>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {subtasks.map((st) => (
                  <SubTaskCard key={st.id} subtask={st} />
                ))}
              </div>
            )}
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
    </div>
  );
}
