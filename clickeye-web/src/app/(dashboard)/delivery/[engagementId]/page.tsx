"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, Boxes, FlaskConical } from "lucide-react";

import { ConsoleHeader, PHASE_LABELS } from "@/components/delivery/console-header";
import { DeliveryStepper } from "@/components/delivery/delivery-stepper";
import { IssueBoard } from "@/components/delivery/issue-board";
import { ReviewList } from "@/components/delivery/review-list";
import { CostCard } from "@/components/delivery/cost-card";
import { GovernancePolicyPanel } from "@/components/delivery/governance-policy-panel";
import { MockModeToggle } from "@/components/delivery/mock-mode-toggle";
import {
  useSessionList,
  useSessionSummary,
  useReviewRounds,
  useSyncLinearStates,
  useLinearTeamStates,
} from "@/hooks/use-orchestrator";
import { useProject } from "@/hooks/use-projects";
import { useMockMode } from "@/stores/mock-mode-store";
import {
  mockProject,
  mockReviewRounds,
  mockSessions,
  mockSummary,
  mockTeamStates,
} from "@/lib/delivery-mock";

const AUTO_PROGRESS_PHASES = ["drafting", "reviewing", "integrating", "approved", "transitioning"];

function CardShell({
  title,
  count,
  children,
}: {
  title: string;
  count?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-[0_1px_2px_rgba(20,24,33,0.05)]">
      <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-4 py-3.5">
        <h2 className="text-[13.5px] font-bold tracking-tight text-[var(--text-primary)]">
          {title}
        </h2>
        {count && (
          <span className="rounded-full bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] font-semibold text-[var(--text-muted)]">
            {count}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}

export default function DeliveryEngagementPage() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const projectId = engagementId;
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");

  const mock = useMockMode((s) => s.enabled);

  // 목업 ON일 때는 sessionId/projectId를 비워 실제 쿼리를 비활성화하고 픽스처로 대체한다.
  const { data: projectData, isError: projectErrorRaw } = useProject(mock ? "" : projectId);

  const {
    data: sessionsData,
    isLoading: sessionsLoadingRaw,
    isError: sessionsErrorRaw,
  } = useSessionList(mock ? "" : projectId);

  const project = mock ? mockProject : projectData;
  const sessions = mock ? mockSessions : sessionsData;

  const firstSessionId = sessions?.items[0]?.id ?? "";
  const activeSessionId = selectedSessionId || firstSessionId;
  const querySessionId = mock ? "" : activeSessionId;

  const {
    data: summaryData,
    isLoading: summaryLoadingRaw,
    isError: summaryErrorRaw,
  } = useSessionSummary(querySessionId);

  const summary = mock ? mockSummary : summaryData;

  const phase = summary?.session?.phase;
  const isAutoProgressPhase = !!phase && AUTO_PROGRESS_PHASES.includes(phase);

  const { data: teamStatesData } = useLinearTeamStates(querySessionId);
  const { data: reviewDataRaw, isError: reviewErrorRaw } = useReviewRounds(
    querySessionId,
    isAutoProgressPhase,
  );
  const syncLinearStates = useSyncLinearStates(querySessionId);

  const teamStates = mock ? mockTeamStates : teamStatesData;
  const reviewData = mock
    ? { items: mockReviewRounds, total: mockReviewRounds.length }
    : reviewDataRaw;

  // 목업 모드에서는 로딩/에러/빈세션 분기를 타지 않도록 상태 플래그를 눌러 둔다.
  const projectError = mock ? false : projectErrorRaw;
  const sessionsLoading = mock ? false : sessionsLoadingRaw;
  const sessionsError = mock ? false : sessionsErrorRaw;
  const summaryLoading = mock ? false : summaryLoadingRaw;
  const summaryError = mock ? false : summaryErrorRaw;
  const reviewError = mock ? false : reviewErrorRaw;

  const subtasks = summary?.subtasks ?? [];
  const reviewRounds = reviewData?.items ?? [];

  const engagementName = project?.name ?? engagementId;

  return (
    <div className="mx-auto w-full max-w-[1440px] space-y-4">
      {/* 목업 데이터 토글 */}
      <div className="flex items-center justify-end">
        <MockModeToggle />
      </div>

      {mock && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          <FlaskConical className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          목업 데이터 표시 중 — 실제 데이터가 아닙니다.
        </div>
      )}

      {/* ===== A. 콘솔 헤더 ===== */}
      <ConsoleHeader
        engagementName={engagementName}
        phase={phase}
        project={project}
        onSync={mock ? () => {} : () => syncLinearStates.mutate()}
        syncing={mock ? false : syncLinearStates.isPending}
      />

      {projectError && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          수주건 정보를 불러오지 못했습니다. ID로 표시합니다.
        </div>
      )}

      {/* 세션 선택 탭 */}
      {sessions && sessions.items.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {sessions.items.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setSelectedSessionId(s.id)}
              className={`flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                s.id === activeSessionId
                  ? "bg-[var(--accent)] text-[var(--accent-fg)] shadow-sm"
                  : "text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              }`}
            >
              {s.title}
              <span className="rounded bg-black/10 px-1 py-0.5 text-[10px] dark:bg-white/15">
                {PHASE_LABELS[s.phase] ?? s.phase}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* 로딩 */}
      {(sessionsLoading || (summaryLoading && !summary)) && (
        <div className="space-y-4">
          <div className="h-16 animate-pulse rounded-2xl bg-[var(--bg-hover)]" />
          <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
            <div className="h-72 animate-pulse rounded-2xl bg-[var(--bg-hover)]" />
            <div className="h-72 animate-pulse rounded-2xl bg-[var(--bg-hover)]" />
          </div>
        </div>
      )}

      {/* 세션 목록 에러 */}
      {sessionsError && !sessionsLoading && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          세션 목록을 불러오지 못했습니다.
        </div>
      )}

      {/* 세션 없음 */}
      {sessions && sessions.items.length === 0 && !sessionsLoading && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--bg-hover)]">
            <Boxes className="h-7 w-7 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            이 수주건에는 아직 작업 세션이 없습니다
          </p>
          <Link
            href={`/projects/${projectId}/ai-team`}
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90"
          >
            작업 세션 만들러 가기
          </Link>
        </div>
      )}

      {/* ===== 관제 화면 ===== */}
      {summary?.session && (
        <div className="space-y-4">
          {/* B. 스텝퍼 */}
          <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-5 py-4 shadow-[0_1px_2px_rgba(20,24,33,0.05)]">
            <DeliveryStepper currentPhase={summary.session.phase} />
          </section>

          {summaryError && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              일부 데이터를 갱신하지 못했습니다.
            </div>
          )}

          {/* 2열 그리드: 좌 보드+리뷰 / 우 레일 */}
          <div className="grid items-start gap-4 lg:grid-cols-[1fr_340px]">
            <div className="flex min-w-0 flex-col gap-4">
              {/* C. 이슈 보드 */}
              <CardShell title="이슈 작업 보드" count={`서브태스크 ${subtasks.length}`}>
                <IssueBoard
                  sessionId={activeSessionId}
                  subtasks={subtasks}
                  teamStates={teamStates ?? []}
                />
              </CardShell>

              {/* E. 검토 대기 */}
              {reviewRounds.length > 0 && (
                <CardShell title="검토 대기" count={`리뷰 라운드 ${reviewRounds.length}`}>
                  {reviewError && (
                    <div className="m-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      리뷰 데이터를 갱신하지 못했습니다.
                    </div>
                  )}
                  <ReviewList rounds={reviewRounds} subtasks={subtasks} />
                </CardShell>
              )}
            </div>

            {/* 우측 레일: D 비용 + F 거버넌스 */}
            <aside className="flex flex-col gap-4">
              <CostCard />
              <GovernancePolicyPanel />
            </aside>
          </div>

          {/* ===== 스코프 푸터 ===== */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-base)] px-4 py-3 text-xs text-[var(--text-secondary)]">
            <span className="inline-flex items-center gap-2">
              <span className="h-2 w-2 flex-none rounded-full bg-emerald-500" aria-hidden="true" />
              <b className="font-semibold text-[var(--text-primary)]">MVP-1·2</b> 이슈 보드 · 파이프라인 · 리뷰 · 비용 (지금 구현)
            </span>
            <span className="inline-flex items-center gap-2 text-[var(--text-muted)]">
              <span className="h-2 w-2 flex-none rounded-full bg-[var(--text-muted)]" aria-hidden="true" />
              회색 = <b className="font-semibold">2차/3차</b> (게이트 결정 이력 · 이슈별 비용 · Temporal 조회 — 백엔드 선행)
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
