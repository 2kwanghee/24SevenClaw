"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight, Loader2 } from "lucide-react";

import { BaseModal } from "@/components/common/base-modal";
import { ReviewDiffViewer } from "@/components/ai-team/review-diff-viewer";
import { useMergeReview, useRejectReview } from "@/hooks/use-orchestrator";
import { useMockMode } from "@/stores/mock-mode-store";
import type { ReviewRoundResponse, SubTaskResponse } from "@/lib/api-client";

function scoreCls(score: number): string {
  if (score >= 8)
    return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300";
  if (score >= 6)
    return "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300";
  return "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300";
}

interface ReviewRowProps {
  round: ReviewRoundResponse;
  subtask?: SubTaskResponse;
}

function ReviewRow({ round, subtask }: ReviewRowProps) {
  const [diffOpen, setDiffOpen] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [reason, setReason] = useState("");

  const t = useTranslations("delivery");
  const merge = useMergeReview();
  const reject = useRejectReview();
  const mock = useMockMode((s) => s.enabled);

  const canAct = round.status === "review_completed";
  const identifier =
    subtask?.linear_identifier ?? subtask?.title ?? t("review.round");

  const handleReject = () => {
    if (!reason.trim()) return;
    reject.mutate({ roundId: round.id, reason: reason.trim() });
    setShowReject(false);
    setReason("");
  };

  return (
    <div className="flex flex-col gap-3 border-b border-[var(--border-subtle)] px-4 py-3.5 last:border-b-0">
      <div className="flex items-center gap-3.5">
        {/* 점수 배지 */}
        <span
          className={`flex h-10 w-10 flex-none items-center justify-center rounded-full font-mono text-[13px] font-bold tabular-nums ${
            round.review_score != null
              ? scoreCls(round.review_score)
              : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
          }`}
        >
          {round.review_score ?? "—"}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 text-[13px] font-semibold">
            <span className="font-mono text-[var(--accent)]">
              {identifier}
            </span>
            {subtask?.linear_identifier && subtask.title && (
              <span className="truncate font-medium text-[var(--text-primary)]">
                {subtask.title}
              </span>
            )}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] text-[var(--text-muted)]">
            <span className="inline-flex items-center gap-1.5">
              {round.main_ai_role}
              {round.sub_ai_role && (
                <>
                  <ArrowRight className="h-3 w-3" aria-hidden="true" />
                  {round.sub_ai_role}
                </>
              )}
            </span>
            {round.diff_summary && (
              <span className="max-w-xs truncate text-[var(--text-secondary)]">
                {round.diff_summary}
              </span>
            )}
            <span>{t("review.roundNumber", { number: round.round_number })}</span>
          </div>
        </div>

        <div className="flex flex-none items-center gap-1.5">
          <button
            type="button"
            onClick={() => setDiffOpen(true)}
            className="rounded-lg border border-[var(--border-medium)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-[11.5px] font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            {t("review.viewDiff")}
          </button>
          {canAct && (
            <>
              <button
                type="button"
                onClick={() =>
                  merge.mutate({
                    roundId: round.id,
                    mergeStrategy: "accept_review",
                  })
                }
                disabled={merge.isPending || mock}
                title={mock ? t("review.disabledMock") : undefined}
                className="inline-flex items-center gap-1 rounded-lg bg-[var(--accent)] px-2.5 py-1.5 text-[11.5px] font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-50"
              >
                {merge.isPending && (
                  <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                )}
                {t("review.merge")}
              </button>
              <button
                type="button"
                onClick={() => setShowReject((v) => !v)}
                disabled={reject.isPending || mock}
                title={mock ? t("review.disabledMock") : undefined}
                className="rounded-lg border border-[var(--border-medium)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-[11.5px] font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover-danger)] hover:text-red-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-50"
              >
                {t("review.reject")}
              </button>
            </>
          )}
        </div>
      </div>

      {/* 거절 사유 입력 */}
      {showReject && canAct && (
        <div className="flex gap-2 pl-[54px]">
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t("review.rejectReasonPlaceholder")}
            aria-label={t("review.rejectReasonLabel")}
            className="flex-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-red-400 focus:outline-none"
          />
          <button
            type="button"
            onClick={handleReject}
            disabled={!reason.trim() || reject.isPending}
            className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:bg-red-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-50 dark:bg-red-950/40 dark:text-red-300"
          >
            {reject.isPending ? (
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            ) : (
              t("review.confirm")
            )}
          </button>
        </div>
      )}

      <BaseModal
        open={diffOpen}
        onClose={() => setDiffOpen(false)}
        size="lg"
        title={t("review.diffModalTitle", { number: round.round_number })}
      >
        <div className="p-4">
          <ReviewDiffViewer round={round} />
        </div>
      </BaseModal>
    </div>
  );
}

interface ReviewListProps {
  rounds: ReviewRoundResponse[];
  subtasks: SubTaskResponse[];
}

export function ReviewList({ rounds, subtasks }: ReviewListProps) {
  const subtaskById = new Map(subtasks.map((s) => [s.id, s]));

  return (
    <div className="flex flex-col">
      {rounds.map((round) => (
        <ReviewRow
          key={round.id}
          round={round}
          subtask={round.subtask_id ? subtaskById.get(round.subtask_id) : undefined}
        />
      ))}
    </div>
  );
}
