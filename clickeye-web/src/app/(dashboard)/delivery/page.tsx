"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Boxes, Loader2, AlertTriangle, ChevronRight, Trash2, X } from "lucide-react";

import { useProjects, useDeleteProject } from "@/hooks/use-projects";
import { useSessionList, useSessionSummary } from "@/hooks/use-orchestrator";
import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog";
import { LlmChatPanel } from "@/components/delivery/llm-chat-panel";
import { MockModeToggle } from "@/components/delivery/mock-mode-toggle";
import { useMockMode } from "@/stores/mock-mode-store";
import { mockProject, mockSessions, mockSummary } from "@/lib/delivery-mock";
import type { ProjectResponse } from "@/lib/api-client";

/**
 * 딜리버리 목록 — 단일 진입점(I-14).
 *
 * 행 클릭은 **선택**이며 진입이 아니다. 요약을 우측 패널에서 확인한 뒤
 * `진입하기`로만 콘솔로 이동한다. 목록 본문은 `ProjectResponse`가 주는 필드만
 * 사용하고(N+1 조회 방지), 세션·서브태스크는 **선택된 프로젝트 1건만** 지연 조회한다.
 *
 * 아직 수집하지 않는 항목(외부연동 blocker, 구독 시트)은 값을 추정해 채우지 않고
 * "도입 후 제공"으로 표시한다.
 */

const DONE_STATUSES = new Set(["approved", "completed", "done", "merged"]);
const RUNNING_STATUSES = new Set(["in_progress", "in_review", "drafting", "reviewing"]);

/**
 * 타임스탬프를 서버·클라이언트가 동일하게 렌더하도록 결정적으로 포맷한다.
 *
 * 상대 시각("2분 전")이나 `toLocaleString()`은 `Date.now()`·타임존에 의존해
 * SSR 결과와 클라이언트 결과가 달라져 하이드레이션 불일치를 만들고,
 * `Date.now()` 자체가 렌더 중 호출 금지(react-hooks/purity) 대상이다.
 * ISO 문자열을 그대로 자르면 두 문제 모두 발생하지 않는다.
 */
function formatUtc(iso: string): string {
  return `${iso.replace("T", " ").slice(0, 16)} UTC`;
}

function StatusPill({ active, label }: { active: boolean; label: string }) {
  return (
    <span
      className={`inline-block shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
        active
          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
          : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
      }`}
    >
      {label}
    </span>
  );
}

export default function DeliveryListPage() {
  const t = useTranslations("delivery");
  const mock = useMockMode((s) => s.enabled);
  const { data, isLoading: isLoadingRaw, isError: isErrorRaw } = useProjects();
  const deleteProject = useDeleteProject();

  // 삭제 대상 프로젝트 (확인 다이얼로그용)
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  // 선택된 프로젝트 — 요약 패널 대상. 선택 ≠ 진입
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const engagements: ProjectResponse[] = mock ? [mockProject] : data?.items ?? [];
  const isLoading = mock ? false : isLoadingRaw;
  const isError = mock ? false : isErrorRaw;
  const selected = engagements.find((p) => p.id === selectedId) ?? null;

  // 선택된 1건만 조회한다 — 목록 렌더에서 프로젝트마다 요청하지 않는다.
  const { data: sessionsRaw, isLoading: sessionsLoading } = useSessionList(
    mock || !selected ? "" : selected.id,
  );
  const sessions = mock && selected ? mockSessions : sessionsRaw;
  const firstSessionId = sessions?.items[0]?.id ?? "";
  const { data: summaryRaw } = useSessionSummary(mock ? "" : firstSessionId);
  const summary = mock && selected ? mockSummary : summaryRaw;

  const closePanel = useCallback(() => setSelectedId(null), []);

  useEffect(() => {
    if (!selected) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closePanel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected, closePanel]);

  const subtasks = summary?.subtasks ?? [];
  const doneCount = subtasks.filter((s) => DONE_STATUSES.has(s.status.toLowerCase())).length;
  const runningCount = subtasks.filter((s) => RUNNING_STATUSES.has(s.status.toLowerCase())).length;
  const currentPhase = sessions?.items[0]?.phase ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)] text-[var(--accent-fg)]">
          <Boxes className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            {t("list.title")}
          </h1>
          <p className="text-xs text-[var(--text-muted)]">{t("list.subtitle")}</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {!isLoading && !isError && engagements.length > 0 && (
            <span className="text-xs text-[var(--text-muted)]">
              {t("list.countLabel")}{" "}
              <b className="font-semibold tabular-nums text-[var(--text-primary)]">
                {engagements.length}
              </b>
            </span>
          )}
          <MockModeToggle />
        </div>
      </div>

      {/* 조직 어시스턴트 — 포트폴리오 RAG(CE-312): 조직 전체 활성 딜리버리 질의 */}
      <LlmChatPanel orgMode mock={mock} />

      {/* 로딩 */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" aria-hidden="true" />
        </div>
      )}

      {/* 에러 */}
      {isError && !isLoading && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          {t("list.errorLoad")}
        </div>
      )}

      {/* 빈 상태 */}
      {!isLoading && !isError && engagements.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--bg-hover)]">
            <Boxes className="h-7 w-7 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">{t("list.empty")}</p>
          <Link
            href="/projects"
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90"
          >
            {t("list.startFromProjects")}
          </Link>
        </div>
      )}

      {/* 수주건 목록 — 카드가 아니라 리스트. 행 선택 → 우측 요약 */}
      {!isLoading && !isError && engagements.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-[var(--border-medium)] text-left">
                  <th className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    {t("list.colProject")}
                  </th>
                  <th className="py-2.5 pr-4 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    {t("list.colStatus")}
                  </th>
                  <th className="py-2.5 pr-4 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    {t("list.colBootstrap")}
                  </th>
                  <th className="py-2.5 pr-4 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    {t("list.colKeys")}
                  </th>
                  <th className="py-2.5 pr-4 text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    {t("list.colUpdated")}
                  </th>
                  <th className="py-2.5 pr-4">
                    <span className="sr-only">{t("list.panelTitle")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {engagements.map((engagement) => {
                  const isSelected = engagement.id === selectedId;
                  return (
                    <tr
                      key={engagement.id}
                      aria-selected={isSelected}
                      onClick={() => setSelectedId(engagement.id)}
                      className={`group cursor-pointer border-b border-[var(--border-subtle)] last:border-b-0 transition-colors hover:bg-[var(--bg-hover)] ${
                        isSelected ? "bg-[var(--bg-hover)]" : ""
                      }`}
                    >
                      <td
                        className={`px-4 py-3 ${
                          isSelected ? "shadow-[inset_3px_0_0_0_var(--accent)]" : ""
                        }`}
                      >
                        <div className="truncate font-semibold text-[var(--text-primary)]">
                          {engagement.name}
                        </div>
                        <div className="truncate font-mono text-[11px] text-[var(--text-muted)]">
                          {engagement.slug}
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <StatusPill
                          active={engagement.status === "active"}
                          label={
                            engagement.status === "active"
                              ? t("list.statusActive")
                              : t("list.statusArchived")
                          }
                        />
                      </td>
                      <td className="py-3 pr-4 text-xs text-[var(--text-secondary)]">
                        {engagement.bootstrap_status}
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex gap-1.5 text-[10px] text-[var(--text-muted)]">
                          <span>A:{t(`keyStatus.${engagement.anthropic_key_status}`)}</span>
                          <span>L:{t(`keyStatus.${engagement.linear_key_status}`)}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-xs tabular-nums text-[var(--text-secondary)]">
                        {formatUtc(engagement.updated_at)}
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center justify-end gap-1">
                          {/* 프로젝트 삭제 — 목업 모드에서는 숨김 */}
                          {!mock && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteTarget({ id: engagement.id, name: engagement.name });
                              }}
                              aria-label={t("deleteProject.ariaLabel", { name: engagement.name })}
                              className="rounded-lg p-1.5 text-[var(--text-muted)] opacity-0 transition-all hover:bg-red-50 hover:text-red-600 focus:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 group-hover:opacity-100 dark:hover:bg-red-950/40"
                            >
                              <Trash2 className="h-4 w-4" aria-hidden="true" />
                            </button>
                          )}
                          {/* 키보드 사용자를 위한 실제 컨트롤 — 행 클릭의 대체 경로 */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedId(engagement.id);
                            }}
                            aria-label={`${engagement.name} — ${t("list.panelTitle")}`}
                            className="rounded-lg p-1.5 text-[var(--text-muted)] transition-colors hover:text-[var(--accent)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                          >
                            <ChevronRight
                              className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                              aria-hidden="true"
                            />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="border-t border-[var(--border-subtle)] px-4 py-2.5 text-xs text-[var(--text-muted)]">
            {t("list.hint")}
          </p>
        </div>
      )}

      {/* 요약 슬라이드 패널 — 진입 전에 판단할 정보를 먼저 보여준다 */}
      {selected && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/10 dark:bg-black/40"
            onClick={closePanel}
            aria-hidden="true"
          />
          <aside
            role="dialog"
            aria-modal="false"
            aria-label={t("list.panelTitle")}
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto border-l border-[var(--border-medium)] bg-[var(--bg-surface)] shadow-2xl"
          >
            <div className="flex items-start gap-3 border-b border-[var(--border-medium)] px-5 py-4">
              <div className="min-w-0">
                <div className="truncate font-mono text-[11px] text-[var(--text-muted)]">
                  {selected.slug}
                </div>
                <h2 className="mt-1 text-lg font-bold leading-snug tracking-tight text-[var(--text-primary)]">
                  {selected.name}
                </h2>
                <div className="mt-2">
                  <StatusPill
                    active={selected.status === "active"}
                    label={
                      selected.status === "active"
                        ? t("list.statusActive")
                        : t("list.statusArchived")
                    }
                  />
                </div>
              </div>
              <button
                type="button"
                onClick={closePanel}
                aria-label={t("list.panelClose")}
                className="ml-auto shrink-0 rounded-lg p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <div className="flex-1 divide-y divide-[var(--border-subtle)] px-5">
              {/* 현재 단계 */}
              <section className="py-4">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  {t("list.phase")}
                </h3>
                <p className="mt-2 text-sm text-[var(--text-primary)]">
                  {sessionsLoading ? (
                    <span className="text-[var(--text-muted)]">{t("list.loading")}…</span>
                  ) : currentPhase ? (
                    t(`phase.${currentPhase}`)
                  ) : (
                    <span className="text-[var(--text-muted)]">{t("list.phaseNone")}</span>
                  )}
                </p>
                {sessions && sessions.items.length > 0 && (
                  <p className="mt-1 text-xs text-[var(--text-muted)]">
                    {t("list.sessions")}{" "}
                    <b className="tabular-nums">{sessions.items.length}</b>
                  </p>
                )}
              </section>

              {/* 서브태스크 진행 — 티켓이 아니라 서브태스크 기준임을 명시 */}
              <section className="py-4">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  {t("list.subLabel")}
                </h3>
                {subtasks.length > 0 ? (
                  <>
                    <div className="mt-2 flex gap-5">
                      <div>
                        <div className="text-xl font-semibold tabular-nums text-[var(--text-primary)]">
                          {doneCount}
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)]">
                          {t("list.subDone")}
                        </div>
                      </div>
                      <div>
                        <div className="text-xl font-semibold tabular-nums text-[var(--text-primary)]">
                          {runningCount}
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)]">
                          {t("list.subOpen")}
                        </div>
                      </div>
                      <div>
                        <div className="text-xl font-semibold tabular-nums text-[var(--text-muted)]">
                          {subtasks.length}
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)]">
                          {t("list.subtasks")}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 h-1 overflow-hidden rounded-full bg-[var(--bg-hover)]">
                      <div
                        className="h-full bg-[var(--accent)]"
                        style={{ width: `${Math.round((doneCount / subtasks.length) * 100)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-[11px] text-[var(--text-muted)]">
                      {t("list.subtaskCaveat")}
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-sm text-[var(--text-muted)]">
                    {sessionsLoading ? `${t("list.loading")}…` : "—"}
                  </p>
                )}
              </section>

              {/* 마지막 활동 */}
              <section className="py-4">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  {t("list.lastActivity")}
                </h3>
                <p className="mt-2 text-sm tabular-nums text-[var(--text-primary)]">
                  {formatUtc(selected.updated_at)}
                </p>
              </section>

              {/* 아직 수집하지 않는 항목 — 값을 추정해 채우지 않는다 */}
              <section className="py-4">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                  {t("list.blocker")} · {t("list.seat")}
                </h3>
                <p className="mt-2 inline-block rounded-md border border-dashed border-[var(--border-medium)] px-2.5 py-1 text-xs text-[var(--text-muted)]">
                  {t("list.notYet")}
                </p>
                <p className="mt-2 text-[11px] text-[var(--text-muted)]">
                  {t("list.notYetHint")}
                </p>
              </section>
            </div>

            {/* 진입은 여기서만 — 행 클릭은 선택일 뿐이다 */}
            <div className="sticky bottom-0 flex gap-2 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-5 py-4">
              <Link
                href={`/delivery/${selected.id}`}
                className="flex-1 rounded-lg bg-[var(--accent)] px-4 py-2.5 text-center text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90"
              >
                {t("list.enter")}
              </Link>
              <Link
                href={`/projects/${selected.id}`}
                className="rounded-lg border border-[var(--border-medium)] px-4 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                {t("list.overview")}
              </Link>
            </div>
          </aside>
        </>
      )}

      {/* 프로젝트 삭제 확인 다이얼로그 */}
      <DeleteProjectDialog
        projectName={deleteTarget?.name ?? ""}
        isOpen={deleteTarget !== null}
        isDeleting={deleteProject.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (!deleteTarget) return;
          deleteProject.mutate(deleteTarget.id, {
            onSuccess: () => {
              toast.success(t("deleteProject.success"));
              setDeleteTarget(null);
              if (deleteTarget.id === selectedId) setSelectedId(null);
            },
            onError: (err) => {
              toast.error(err.message || t("deleteProject.fail"));
              setDeleteTarget(null);
            },
          });
        }}
      />
    </div>
  );
}
