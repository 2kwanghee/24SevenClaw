"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { AlertTriangle, Boxes, FlaskConical, Trash2 } from "lucide-react";

import { ConsoleHeader } from "@/components/delivery/console-header";
import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog";
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
import { useProject, useDeleteProject } from "@/hooks/use-projects";
import { useLlmLedgerSummary } from "@/hooks/use-llm-ledger";
import { useGovernancePolicy } from "@/hooks/use-governance";
import { useProjectOverrides } from "@/hooks/use-contracts";
import { useMockMode } from "@/stores/mock-mode-store";
import { useRBACStore } from "@/stores/rbac-store";
import {
  mockGovernancePolicy,
  mockLedgerSummary,
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
  const t = useTranslations("delivery");
  const router = useRouter();
  const { engagementId } = useParams<{ engagementId: string }>();
  const projectId = engagementId;
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const deleteProject = useDeleteProject();

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

  // D. 비용 카드 — LLM 원장은 settings:manage 권한 전용.
  const rbacLoaded = useRBACStore((s) => s.loaded);
  const canViewLedger = useRBACStore((s) => s.hasPermission("settings:manage"));
  const ledgerRestricted = !mock && rbacLoaded && !canViewLedger;
  const ledgerEnabled = !mock && rbacLoaded && canViewLedger;

  const {
    data: ledgerData,
    isLoading: ledgerFetchingRaw,
    isError: ledgerErrorRaw,
  } = useLlmLedgerSummary(ledgerEnabled ? projectId : "");

  const ledgerSummary = mock ? mockLedgerSummary : (ledgerData ?? null);
  const ledgerLoading = mock
    ? false
    : ledgerRestricted
      ? false
      : !rbacLoaded || ledgerFetchingRaw;
  const ledgerError = mock ? false : ledgerErrorRaw;

  // F. 거버넌스 정책 — 목업 ON일 때는 실 API 호출을 비활성화하고 픽스처로 대체한다.
  const {
    data: policyData,
    isLoading: policyLoadingRaw,
    isError: policyErrorRaw,
  } = useGovernancePolicy(!mock);
  const { data: overridesData } = useProjectOverrides(mock ? "" : projectId);

  const governancePolicy = mock ? mockGovernancePolicy : (policyData ?? null);
  const governanceLoading = mock ? false : policyLoadingRaw;
  const governanceError = mock ? false : policyErrorRaw;
  const contractOverrides = mock ? [] : (overridesData?.items ?? undefined);

  const subtasks = summary?.subtasks ?? [];
  const reviewRounds = reviewData?.items ?? [];

  const engagementName = project?.name ?? engagementId;

  return (
    <div className="mx-auto w-full max-w-[1440px] space-y-4">
      {/* 목업 데이터 토글 + 프로젝트 삭제 */}
      <div className="flex items-center justify-end gap-2">
        {/* 프로젝트 삭제 — 목업 모드에서는 숨김 */}
        {!mock && project && (
          <button
            type="button"
            onClick={() => setDeleteOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-red-300 bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950/40"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            {t("deleteProject.action")}
          </button>
        )}
        <MockModeToggle />
      </div>

      {mock && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
          <FlaskConical className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {t("mock.banner")}
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
          {t("console.projectError")}
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
                {t.has(`phase.${s.phase}`) ? t(`phase.${s.phase}`) : s.phase}
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
          {t("console.sessionsError")}
        </div>
      )}

      {/* 세션 없음 */}
      {sessions && sessions.items.length === 0 && !sessionsLoading && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--bg-hover)]">
            <Boxes className="h-7 w-7 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            {t("console.noSessions")}
          </p>
          <Link
            href={`/projects/${projectId}/ai-team`}
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90"
          >
            {t("console.createSession")}
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
              {t("console.summaryError")}
            </div>
          )}

          {/* 2열 그리드: 좌 보드+리뷰 / 우 레일 */}
          <div className="grid items-start gap-4 lg:grid-cols-[1fr_340px]">
            <div className="flex min-w-0 flex-col gap-4">
              {/* C. 이슈 보드 */}
              <CardShell
                title={t("console.issueBoardTitle")}
                count={t("console.subtaskCount", { count: subtasks.length })}
              >
                <IssueBoard
                  sessionId={activeSessionId}
                  subtasks={subtasks}
                  teamStates={teamStates ?? []}
                />
              </CardShell>

              {/* E. 검토 대기 */}
              {reviewRounds.length > 0 && (
                <CardShell
                  title={t("console.reviewTitle")}
                  count={t("console.reviewCount", { count: reviewRounds.length })}
                >
                  {reviewError && (
                    <div className="m-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      {t("console.reviewError")}
                    </div>
                  )}
                  <ReviewList rounds={reviewRounds} subtasks={subtasks} />
                </CardShell>
              )}
            </div>

            {/* 우측 레일: D 비용 + F 거버넌스 */}
            <aside className="flex flex-col gap-4">
              <CostCard
                summary={ledgerSummary}
                isLoading={ledgerLoading}
                isError={ledgerError}
                restricted={ledgerRestricted}
              />
              <GovernancePolicyPanel
                policy={governancePolicy}
                isLoading={governanceLoading}
                isError={governanceError}
                overrides={contractOverrides}
              />
            </aside>
          </div>

          {/* ===== 스코프 푸터 ===== */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-base)] px-4 py-3 text-xs text-[var(--text-secondary)]">
            <span className="inline-flex items-center gap-2">
              <span className="h-2 w-2 flex-none rounded-full bg-emerald-500" aria-hidden="true" />
              {t.rich("console.scopeCurrent", {
                b: (chunks) => (
                  <b className="font-semibold text-[var(--text-primary)]">{chunks}</b>
                ),
              })}
            </span>
            <span className="inline-flex items-center gap-2 text-[var(--text-muted)]">
              <span className="h-2 w-2 flex-none rounded-full bg-[var(--text-muted)]" aria-hidden="true" />
              {t.rich("console.scopeFuture", {
                b: (chunks) => <b className="font-semibold">{chunks}</b>,
              })}
            </span>
          </div>
        </div>
      )}

      {/* 프로젝트 삭제 확인 다이얼로그 — 성공 시 목록으로 이동 */}
      <DeleteProjectDialog
        projectName={project?.name ?? engagementName}
        isOpen={deleteOpen}
        isDeleting={deleteProject.isPending}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => {
          deleteProject.mutate(projectId, {
            onSuccess: () => {
              toast.success(t("deleteProject.success"));
              setDeleteOpen(false);
              router.push("/delivery");
            },
            onError: (err) => {
              toast.error(err.message || t("deleteProject.fail"));
              setDeleteOpen(false);
            },
          });
        }}
      />
    </div>
  );
}
