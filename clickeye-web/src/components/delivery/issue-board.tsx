"use client";

import { useTranslations } from "next-intl";
import { Loader2, Link2, Inbox } from "lucide-react";

import { IssueCard } from "@/components/delivery/issue-card";
import { usePushToLinear } from "@/hooks/use-orchestrator";
import type { LinearTeamState, SubTaskResponse } from "@/lib/api-client";

interface IssueBoardProps {
  sessionId: string;
  subtasks: SubTaskResponse[];
  teamStates: LinearTeamState[];
}

const UNLINKED_KEY = "__unlinked__";

export function IssueBoard({ sessionId, subtasks, teamStates }: IssueBoardProps) {
  const t = useTranslations("delivery");
  const pushToLinear = usePushToLinear();

  // ai-team/page.tsx 와 동일한 순번·의존성 계산
  const dependencyMap = new Map(subtasks.map((s) => [s.title, s]));
  const sortedByOrder = [...subtasks].sort((a, b) => a.order_index - b.order_index);
  const orderNumById = new Map(sortedByOrder.map((s, idx) => [s.id, idx + 1]));
  const total = subtasks.length;

  // linear_state 기준으로 컬럼 그룹핑
  const linked = subtasks.filter((s) => !!s.linear_issue_id && !!s.linear_state);
  const stateColumns = teamStates.map((state) => ({
    state,
    items: linked
      .filter((s) => s.linear_state === state.name)
      .sort((a, b) => a.order_index - b.order_index),
  }));

  // 컬럼에 매칭되지 않은 항목(미연동 + 컬럼 미매칭 linked)은 "미연동" 컬럼으로
  const matchedIds = new Set(stateColumns.flatMap((c) => c.items.map((i) => i.id)));
  const unlinkedItems = subtasks
    .filter((s) => !matchedIds.has(s.id))
    .sort((a, b) => a.order_index - b.order_index);
  const hasUnregistered = unlinkedItems.some((s) => !s.linear_issue_id);
  // 이 컬럼은 진짜 미연동(linear_issue_id 없음) + 상태 미매칭(연동됐으나 팀 상태 컬럼에
  // 매칭 안 됨) 항목을 함께 담는다. 후자가 섞이면 라벨을 "미연동 · 기타"로 정직하게 표기.
  const hasMismatched = unlinkedItems.some((s) => !!s.linear_issue_id);
  const unlinkedTitle = hasMismatched
    ? t("issues.unlinkedOther")
    : t("issues.unlinked");

  const renderCard = (st: SubTaskResponse) => (
    <IssueCard
      key={st.id}
      subtask={st}
      sessionId={sessionId}
      orderNum={orderNumById.get(st.id) ?? 0}
      total={total}
      dependencyMap={dependencyMap}
    />
  );

  if (subtasks.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] py-16">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--bg-hover)]">
          <Inbox className="h-6 w-6 text-[var(--text-muted)]" aria-hidden="true" />
        </div>
        <p className="text-sm text-[var(--text-muted)]">{t("issues.empty")}</p>
      </div>
    );
  }

  return (
    <div className="flex gap-3 overflow-x-auto p-3.5">
      {/* 미연동 컬럼 (항목이 있을 때만) */}
      {unlinkedItems.length > 0 && (
        <BoardColumn
          key={UNLINKED_KEY}
          title={unlinkedTitle}
          count={unlinkedItems.length}
          colorDot={null}
          muted
        >
          {hasUnregistered && (
            <button
              type="button"
              onClick={() => pushToLinear.mutate({ sessionId })}
              disabled={pushToLinear.isPending}
              className="mb-1 flex w-full items-center justify-center gap-1.5 rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] px-3 py-2 text-xs font-semibold text-[var(--accent)] transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-50"
            >
              {pushToLinear.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Link2 className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              {t("issues.pushToLinear")}
            </button>
          )}
          {unlinkedItems.map(renderCard)}
        </BoardColumn>
      )}

      {/* Linear 상태별 컬럼 (동적) */}
      {stateColumns.map(({ state, items }) => (
        <BoardColumn
          key={state.name}
          title={state.name}
          count={items.length}
          colorDot={state.color}
        >
          {items.length === 0 ? (
            <p className="rounded-lg border border-dashed border-[var(--border-subtle)] py-6 text-center text-[11px] text-[var(--text-muted)]">
              {t("issues.columnEmpty")}
            </p>
          ) : (
            items.map(renderCard)
          )}
        </BoardColumn>
      ))}
    </div>
  );
}

interface BoardColumnProps {
  title: string;
  count: number;
  colorDot: string | null;
  muted?: boolean;
  children: React.ReactNode;
}

function BoardColumn({ title, count, colorDot, muted, children }: BoardColumnProps) {
  return (
    <div className="flex w-56 flex-none flex-col gap-2.5">
      <div className="flex items-center gap-2 px-1">
        {colorDot ? (
          <span
            className="h-2 w-2 flex-none rounded-sm"
            style={{ backgroundColor: colorDot }}
            aria-hidden="true"
          />
        ) : (
          <span
            className="h-2 w-2 flex-none rounded-sm bg-[var(--border-medium)]"
            aria-hidden="true"
          />
        )}
        <h3
          className={`truncate text-xs font-bold ${
            muted ? "text-[var(--text-muted)]" : "text-[var(--text-secondary)]"
          }`}
        >
          {title}
        </h3>
        <span className="ml-auto font-mono text-[11px] text-[var(--text-muted)]">
          {count}
        </span>
      </div>
      <div className="flex flex-col gap-2.5">{children}</div>
    </div>
  );
}
