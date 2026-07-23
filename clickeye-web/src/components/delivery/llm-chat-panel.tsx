"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Bot,
  FlaskConical,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";

import {
  useLlmChat,
  useLlmChatOrg,
  useLlmProgress,
  useSendLlmFeedback,
} from "@/hooks/use-llm";
import { ApiClientError, type LlmSource } from "@/lib/api-client";

interface LlmChatPanelProps {
  /** 딜리버리(프로젝트) 모드에서 필수. orgMode 에서는 사용하지 않는다. */
  projectId?: string;
  /** 목업 모드에서는 실 API 호출을 막고 안내만 노출한다. */
  mock?: boolean;
  /**
   * 조직 어시스턴트 모드(포트폴리오, CE-312). true 면 /llm/chat/org 를 호출하고
   * 진행상황·피드백(프로젝트 스코프)은 숨긴다. delivery_id 는 서버가 org 로 매핑.
   */
  orgMode?: boolean;
}

/** 에러가 clickeye-llm 미가용(503) 인지 판별한다. */
function isUnavailable(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 503;
}

function CardFrame({
  children,
  orgMode = false,
}: {
  children: React.ReactNode;
  orgMode?: boolean;
}) {
  const t = useTranslations("delivery");
  return (
    <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-[0_1px_2px_rgba(20,24,33,0.05)]">
      <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-4 py-3.5">
        <Sparkles className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" />
        <div className="min-w-0">
          <h2 className="text-[13.5px] font-bold tracking-tight text-[var(--text-primary)]">
            {orgMode ? t("orgChat.title") : t("chat.title")}
          </h2>
          {orgMode && (
            <p className="text-[11px] text-[var(--text-muted)]">
              {t("orgChat.subtitle")}
            </p>
          )}
        </div>
      </div>
      {children}
    </section>
  );
}

function SourceList({ sources }: { sources: LlmSource[] }) {
  const t = useTranslations("delivery");
  if (sources.length === 0) return null;
  return (
    <div className="mt-2 flex flex-col gap-1.5 border-t border-[var(--border-subtle)] pt-2">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
        {t("chat.sources")}
      </span>
      {sources.map((s, i) => (
        <div
          key={`${s.source_id}-${s.chunk_index}-${i}`}
          className="flex flex-col gap-0.5 rounded-lg bg-[var(--bg-base)] px-2.5 py-1.5"
        >
          <span className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--text-secondary)]">
            <span className="truncate">{s.source_id}</span>
            <span className="ml-auto shrink-0 font-mono tabular-nums text-[var(--text-muted)]">
              {s.score.toFixed(2)}
            </span>
          </span>
          <span className="line-clamp-2 text-[11px] leading-relaxed text-[var(--text-muted)]">
            {s.text}
          </span>
        </div>
      ))}
    </div>
  );
}

interface FeedbackControlsProps {
  projectId: string;
  /** 평가 대상 chat 응답 식별자. key 로도 사용해 새 답변마다 상태를 리셋한다. */
  chatId: string | undefined;
  query: string;
  answer: string;
  sources: string[];
}

/** 답변 하단 👍/👎 피드백(P2-MVP). 제출 성공 시 버튼 대신 감사 문구를 표시한다. */
function FeedbackControls({
  projectId,
  chatId,
  query,
  answer,
  sources,
}: FeedbackControlsProps) {
  const t = useTranslations("delivery");
  const feedback = useSendLlmFeedback(projectId);
  const [downOpen, setDownOpen] = useState(false);
  const [comment, setComment] = useState("");

  const submit = (rating: "up" | "down") => {
    if (feedback.isPending || feedback.isSuccess) return;
    feedback.mutate({
      chat_id: chatId ?? null,
      query,
      answer,
      rating,
      comment: rating === "down" && comment.trim() ? comment.trim() : null,
      sources,
    });
  };

  if (feedback.isSuccess) {
    return (
      <p className="mt-2 border-t border-[var(--border-subtle)] pt-2 text-[11px] text-[var(--text-muted)]">
        {t("chat.feedback.thanks")}
      </p>
    );
  }

  const iconButton =
    "inline-flex h-7 w-7 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <div className="mt-2 flex flex-col gap-1.5 border-t border-[var(--border-subtle)] pt-2">
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => submit("up")}
          disabled={feedback.isPending}
          aria-label={t("chat.feedback.up")}
          title={t("chat.feedback.up")}
          className={iconButton}
        >
          <ThumbsUp className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => setDownOpen((v) => !v)}
          disabled={feedback.isPending}
          aria-label={t("chat.feedback.down")}
          title={t("chat.feedback.down")}
          aria-pressed={downOpen}
          className={`${iconButton} ${downOpen ? "bg-[var(--bg-hover)] text-[var(--text-primary)]" : ""}`}
        >
          <ThumbsDown className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
        {feedback.isError && (
          <span className="text-[11px] text-red-700 dark:text-red-300">
            {t("chat.feedback.fail")}
          </span>
        )}
      </div>
      {downOpen && (
        <div className="flex items-end gap-2">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
            placeholder={t("chat.feedback.commentPlaceholder")}
            aria-label={t("chat.feedback.commentPlaceholder")}
            className="min-h-[2.25rem] flex-1 resize-none rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-2.5 py-1.5 text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          />
          <button
            type="button"
            onClick={() => submit("down")}
            disabled={feedback.isPending}
            className="inline-flex h-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] px-2.5 text-[11px] font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t("chat.feedback.submit")}
          </button>
        </div>
      )}
    </div>
  );
}

export function LlmChatPanel({
  projectId,
  mock = false,
  orgMode = false,
}: LlmChatPanelProps) {
  const t = useTranslations("delivery");
  const [query, setQuery] = useState("");
  const [progressRequested, setProgressRequested] = useState(false);

  // 두 뮤테이션을 무조건 인스턴스화하고(hook 규칙) 모드에 따라 선택한다.
  // 뮤테이션은 mutate() 호출 시에만 발화하므로 유휴 인스턴스는 부작용이 없다.
  const projectChat = useLlmChat(projectId ?? "");
  const orgChat = useLlmChatOrg();
  const chat = orgMode ? orgChat : projectChat;
  // 진행상황은 프로젝트 스코프 — orgMode 에서는 비활성.
  const progress = useLlmProgress(
    projectId ?? "",
    !mock && !orgMode && !!projectId && progressRequested,
  );

  // 목업 모드 — 실 호출 없이 안내만.
  if (mock) {
    return (
      <CardFrame orgMode={orgMode}>
        <div className="flex flex-col items-center gap-2 p-6 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--bg-hover)]">
            <FlaskConical className="h-5 w-5 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-xs font-medium text-[var(--text-secondary)]">
            {t("chat.mockTitle")}
          </p>
          <p className="text-[11px] text-[var(--text-muted)]">{t("chat.mockDesc")}</p>
        </div>
      </CardFrame>
    );
  }

  const handleSend = () => {
    const q = query.trim();
    if (!q || chat.isPending) return;
    chat.mutate(q);
  };

  const chatUnavailable = isUnavailable(chat.error);
  const progressUnavailable = isUnavailable(progress.error);

  return (
    <CardFrame orgMode={orgMode}>
      <div className="flex flex-col gap-3 p-4">
        {/* 진행상황 확인 — 프로젝트 스코프 전용(orgMode 숨김) */}
        {!orgMode && (
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => {
              setProgressRequested(true);
              if (progressRequested) void progress.refetch();
            }}
            disabled={progress.isFetching}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Bot className="h-3.5 w-3.5" aria-hidden="true" />
            {progress.isFetching ? t("chat.progressLoading") : t("chat.progressButton")}
          </button>

          {progressRequested && progressUnavailable && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {t("chat.unavailable")}
            </div>
          )}
          {progressRequested &&
            progress.isError &&
            !progressUnavailable && (
              <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[11px] text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {t("chat.progressError")}
              </div>
            )}
          {progress.data && (
            <div className="rounded-lg bg-[var(--bg-base)] px-3 py-2.5">
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-[var(--text-secondary)]">
                {progress.data.summary}
              </p>
              <p className="mt-1.5 text-[11px] text-[var(--text-muted)]">
                {t("chat.knowledgeItems", { count: progress.data.knowledge_items })}
              </p>
            </div>
          )}
        </div>
        )}

        {/* 답변 영역 */}
        {chat.isPending && (
          <div className="flex animate-pulse flex-col gap-2 rounded-lg bg-[var(--bg-base)] px-3 py-2.5">
            <div className="h-2.5 w-3/4 rounded bg-[var(--bg-hover)]" />
            <div className="h-2.5 w-full rounded bg-[var(--bg-hover)]" />
          </div>
        )}
        {chatUnavailable && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {t("chat.unavailable")}
          </div>
        )}
        {chat.isError && !chatUnavailable && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[11px] text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {t("chat.error")}
          </div>
        )}
        {chat.data && !chat.isPending && (
          <div className="rounded-lg bg-[var(--bg-base)] px-3 py-2.5">
            <p className="whitespace-pre-wrap text-xs leading-relaxed text-[var(--text-primary)]">
              {chat.data.answer}
            </p>
            <SourceList sources={chat.data.sources} />
            {/* 피드백은 프로젝트 스코프 전용(orgMode 에는 /feedback 경로 없음) */}
            {!orgMode && projectId && (
              <FeedbackControls
                key={chat.data.chat_id}
                projectId={projectId}
                chatId={chat.data.chat_id}
                query={chat.variables ?? ""}
                answer={chat.data.answer}
                sources={[...new Set(chat.data.sources.map((s) => s.source_id))]}
              />
            )}
          </div>
        )}

        {/* 질문 입력 */}
        <div className="flex items-end gap-2">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            rows={2}
            placeholder={orgMode ? t("orgChat.placeholder") : t("chat.placeholder")}
            aria-label={orgMode ? t("orgChat.title") : t("chat.title")}
            className="min-h-[2.5rem] flex-1 resize-none rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3 py-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!query.trim() || chat.isPending}
            aria-label={t("chat.send")}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <p className="text-[11px] leading-relaxed text-[var(--text-muted)]">
          {orgMode ? t("orgChat.hint") : t("chat.hint")}
        </p>
      </div>
    </CardFrame>
  );
}
