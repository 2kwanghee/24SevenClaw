"use client";

import { useEffect, useId } from "react";
import { ExternalLink, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { useTicketDetail } from "@/hooks/use-observability";
import type { DeliveryBoardTicketItem } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface DeliveryBoardTicketDetailPanelProps {
  ticket: DeliveryBoardTicketItem;
  open: boolean;
  onClose: () => void;
}

function formatDateTime(iso: string | null | undefined, locale: string): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** 딜리버리 보드 티켓 상세 패널 — 카드 클릭 시 우측 슬라이드로 Linear 원본을 보여준다.
 * lazy 조회(open=true 일 때만), 로딩 스켈레톤 / available:false 안내 / ESC·바깥 클릭 닫기. */
export function DeliveryBoardTicketDetailPanel({
  ticket,
  open,
  onClose,
}: DeliveryBoardTicketDetailPanelProps) {
  const t = useTranslations("observability.dashboard.deliveryBoard");
  const tA = useTranslations("common.aria");
  const locale = useLocale();
  const titleId = useId();

  const hasIssueId = Boolean(ticket.issue_id);
  const { data, isLoading, error } = useTicketDetail(ticket.issue_id, open);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const loading = hasIssueId && isLoading;
  const unavailable =
    !hasIssueId || Boolean(error) || (data !== undefined && data.available === false);
  const detail = data && data.available ? data : null;
  const createdAt = formatDateTime(detail?.created_at, locale);
  const updatedAt = formatDateTime(detail?.updated_at, locale);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm"
      role="presentation"
      onClick={onClose}
    >
      <div
        className="flex h-full w-full flex-col bg-[var(--bg-surface)] shadow-2xl sm:max-w-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
          <div id={titleId} className="min-w-0">
            <span className="mr-1 text-xs font-medium text-[var(--text-muted)]">
              {ticket.key}
            </span>
            <span className="text-sm font-semibold text-[var(--text-primary)]">
              {detail?.title ?? ticket.title}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={tA("close")}
            className="rounded-md p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* 본문 */}
        <div className="flex-1 overflow-y-auto px-4 py-4 text-sm">
          {loading && (
            <div className="space-y-3" aria-hidden="true">
              <div className="h-4 w-1/3 animate-pulse rounded bg-[var(--bg-hover)]" />
              <div className="h-4 w-2/3 animate-pulse rounded bg-[var(--bg-hover)]" />
              <div className="h-20 w-full animate-pulse rounded bg-[var(--bg-hover)]" />
            </div>
          )}

          {!loading && unavailable && (
            <p className="py-6 text-center text-[var(--text-muted)]">{t("detail.unavailable")}</p>
          )}

          {!loading && detail && (
            <div className="space-y-4">
              {/* 메타 */}
              <div className="flex flex-wrap gap-2">
                {detail.state_name && (
                  <span className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-2 py-0.5 text-xs font-medium text-[var(--text-secondary)]">
                    {detail.state_name}
                  </span>
                )}
                {detail.priority_label && (
                  <span className="rounded-full border border-[var(--border-subtle)] px-2 py-0.5 text-xs text-[var(--text-secondary)]">
                    {t("detail.priority")}: {detail.priority_label}
                  </span>
                )}
              </div>

              <dl className="space-y-1.5 text-xs">
                {detail.assignee && (
                  <div className="flex gap-2">
                    <dt className="w-16 shrink-0 text-[var(--text-muted)]">
                      {t("detail.assignee")}
                    </dt>
                    <dd className="text-[var(--text-primary)]">{detail.assignee}</dd>
                  </div>
                )}
                {detail.labels && detail.labels.length > 0 && (
                  <div className="flex gap-2">
                    <dt className="w-16 shrink-0 text-[var(--text-muted)]">
                      {t("detail.labels")}
                    </dt>
                    <dd className="flex flex-wrap gap-1">
                      {detail.labels.map((label) => (
                        <span
                          key={label}
                          className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[var(--text-secondary)]"
                        >
                          {label}
                        </span>
                      ))}
                    </dd>
                  </div>
                )}
                {createdAt && (
                  <div className="flex gap-2">
                    <dt className="w-16 shrink-0 text-[var(--text-muted)]">
                      {t("detail.createdAt")}
                    </dt>
                    <dd className="text-[var(--text-secondary)]">{createdAt}</dd>
                  </div>
                )}
                {updatedAt && (
                  <div className="flex gap-2">
                    <dt className="w-16 shrink-0 text-[var(--text-muted)]">
                      {t("detail.updatedAt")}
                    </dt>
                    <dd className="text-[var(--text-secondary)]">{updatedAt}</dd>
                  </div>
                )}
              </dl>

              {/* 본문 (줄바꿈 보존) */}
              {detail.description && (
                <div>
                  <h3 className="mb-1 text-xs font-semibold text-[var(--text-secondary)]">
                    {t("detail.description")}
                  </h3>
                  <p className="whitespace-pre-wrap break-words text-xs leading-relaxed text-[var(--text-primary)]">
                    {detail.description}
                  </p>
                </div>
              )}

              {/* 코멘트 */}
              <div>
                <h3 className="mb-1.5 text-xs font-semibold text-[var(--text-secondary)]">
                  {t("detail.comments")} ({detail.comments?.length ?? 0})
                </h3>
                {detail.comments && detail.comments.length > 0 ? (
                  <ul className="space-y-2">
                    {detail.comments.map((comment, idx) => (
                      <li
                        key={idx}
                        className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-2"
                      >
                        <div className="mb-0.5 flex items-center justify-between gap-2 text-[10px] text-[var(--text-muted)]">
                          <span className="font-medium text-[var(--text-secondary)]">
                            {comment.author ?? t("detail.unknownAuthor")}
                          </span>
                          <time>{formatDateTime(comment.created_at, locale) ?? ""}</time>
                        </div>
                        <p className="whitespace-pre-wrap break-words text-xs text-[var(--text-primary)]">
                          {comment.body}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[var(--text-muted)]">{t("detail.noComments")}</p>
                )}
              </div>

              {/* Linear 원문 링크 */}
              {detail.url && (
                <a
                  href={detail.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5",
                    "text-xs font-medium text-[var(--accent)] transition-colors hover:bg-[var(--bg-hover)]",
                  )}
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                  {t("detail.openInLinear")}
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
