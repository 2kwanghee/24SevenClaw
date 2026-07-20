"use client";

import { useState } from "react";
import {
  Check,
  X,
  GitMerge,
  Loader2,
  ChevronDown,
  ChevronUp,
  Star,
} from "lucide-react";

import type { ReviewRoundResponse, MergeStrategy } from "@/lib/api-client";
import { useReviewDiff, useMergeReview, useRejectReview } from "@/hooks/use-orchestrator";

const STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  draft_submitted: { label: "초안 제출", cls: "bg-blue-50 text-blue-700" },
  review_in_progress: { label: "리뷰 중", cls: "bg-amber-50 text-amber-700" },
  review_completed: { label: "리뷰 완료", cls: "bg-emerald-50 text-emerald-700" },
  merged: { label: "병합됨", cls: "bg-violet-50 text-violet-700" },
  rejected: { label: "거절됨", cls: "bg-red-50 text-red-700" },
};

interface ReviewDiffViewerProps {
  round: ReviewRoundResponse;
}

export function ReviewDiffViewer({ round }: ReviewDiffViewerProps) {
  const [expanded, setExpanded] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [showReject, setShowReject] = useState(false);

  const { data: diff, isLoading: diffLoading } = useReviewDiff(
    expanded && round.review_content ? round.id : "",
  );

  const merge = useMergeReview();
  const reject = useRejectReview();

  const statusCfg = STATUS_LABELS[round.status] ?? STATUS_LABELS.draft_submitted;
  const canAct = round.status === "review_completed";

  const handleMerge = (strategy: MergeStrategy) => {
    merge.mutate({ roundId: round.id, mergeStrategy: strategy });
  };

  const handleReject = () => {
    if (!rejectReason.trim()) return;
    reject.mutate({ roundId: round.id, reason: rejectReason.trim() });
    setShowReject(false);
    setRejectReason("");
  };

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* 헤더 */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-[var(--bg-hover)]"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-[var(--text-secondary)]">
            Round #{round.round_number}
          </span>
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${statusCfg.cls}`}>
            {statusCfg.label}
          </span>
          {round.review_score != null && (
            <span className="flex items-center gap-0.5 text-xs text-amber-600">
              <Star className="h-3 w-3" />
              {round.review_score}
            </span>
          )}
          <span className="text-xs text-[var(--text-muted)]">
            {round.main_ai_role}
            {round.sub_ai_role ? ` → ${round.sub_ai_role}` : ""}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-[var(--text-muted)]" />
        ) : (
          <ChevronDown className="h-4 w-4 text-[var(--text-muted)]" />
        )}
      </button>

      {/* 콘텐츠 */}
      {expanded && (
        <div className="border-t border-[var(--border-subtle)] p-4 space-y-4">
          {/* 초안 */}
          <div>
            <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
              초안 ({round.main_ai_role})
            </p>
            <pre className="max-h-48 overflow-auto rounded-lg bg-[var(--bg-hover)] p-3 text-xs text-[var(--text-secondary)] whitespace-pre-wrap">
              {round.draft_content}
            </pre>
          </div>

          {/* 리뷰 콘텐츠 */}
          {round.review_content && (
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
                리뷰 ({round.sub_ai_role ?? "—"})
                {round.review_type && (
                  <span className="ml-2 rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] text-[var(--text-secondary)]">
                    {round.review_type}
                  </span>
                )}
              </p>
              <pre className="max-h-48 overflow-auto rounded-lg bg-[var(--bg-hover)] p-3 text-xs text-[var(--text-secondary)] whitespace-pre-wrap">
                {round.review_content}
              </pre>
            </div>
          )}

          {/* Diff 요약 */}
          {diffLoading && (
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
              <Loader2 className="h-3 w-3 animate-spin" />
              diff 로딩 중...
            </div>
          )}
          {diff?.diff_summary && (
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
                변경 요약
              </p>
              <pre className="max-h-32 overflow-auto rounded-lg bg-emerald-50 p-3 text-xs text-emerald-700 whitespace-pre-wrap">
                {diff.diff_summary}
              </pre>
            </div>
          )}

          {/* 병합된 콘텐츠 */}
          {round.merged_content && (
            <div>
              <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
                병합 결과 ({round.merge_strategy})
              </p>
              <pre className="max-h-48 overflow-auto rounded-lg bg-violet-50 p-3 text-xs text-violet-700 whitespace-pre-wrap">
                {round.merged_content}
              </pre>
            </div>
          )}

          {/* 액션 버튼 (review_completed 상태일 때만) */}
          {canAct && (
            <div className="flex flex-wrap items-center gap-2 border-t border-[var(--border-subtle)] pt-3">
              <button
                type="button"
                onClick={() => handleMerge("accept_draft")}
                disabled={merge.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
              >
                <Check className="h-3 w-3" />
                초안 수락
              </button>
              <button
                type="button"
                onClick={() => handleMerge("accept_review")}
                disabled={merge.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:opacity-50"
              >
                <GitMerge className="h-3 w-3" />
                리뷰 수락
              </button>
              <button
                type="button"
                onClick={() => setShowReject(!showReject)}
                disabled={reject.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-100 disabled:opacity-50"
              >
                <X className="h-3 w-3" />
                거절
              </button>
              {merge.isPending && (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--text-muted)]" />
              )}
            </div>
          )}

          {/* 거절 사유 입력 */}
          {showReject && canAct && (
            <div className="flex gap-2">
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="거절 사유를 입력하세요..."
                className="flex-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-red-300 focus:outline-none"
                aria-label="거절 사유"
              />
              <button
                type="button"
                onClick={handleReject}
                disabled={!rejectReason.trim() || reject.isPending}
                className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-100 disabled:opacity-50"
              >
                {reject.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  "확인"
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
