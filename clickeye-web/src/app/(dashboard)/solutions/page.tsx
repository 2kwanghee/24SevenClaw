"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  Sparkles,
  Plus,
  Loader2,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { prototypeSessions, ApiClientError } from "@/lib/api-client";
import type { PrototypeSessionResponse } from "@/lib/api-client";

const STATUS_CONFIG: Record<
  PrototypeSessionResponse["status"],
  { icon: typeof CheckCircle2; className: string }
> = {
  completed: {
    icon: CheckCircle2,
    className: "text-emerald-700",
  },
  generating: {
    icon: Loader2,
    className: "animate-spin text-yellow-600",
  },
  pending: {
    icon: Clock,
    className: "text-[var(--text-muted)]",
  },
  failed: {
    icon: XCircle,
    className: "text-red-700",
  },
};

export default function SolutionsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const t = useTranslations("solutions.page");
  const tStatus = useTranslations("solutions.status");

  const [sessions, setSessions] = useState<PrototypeSessionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    const fetchSessions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await prototypeSessions.list(token, { limit: 20 });
        setSessions(Array.isArray(result) ? result : []);
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError(err.detail);
        } else {
          setError(t("loadError"));
        }
      } finally {
        setIsLoading(false);
      }
    };

    void fetchSessions();
  }, [token, t]);

  return (
    <div className="mx-auto max-w-3xl">
      {/* 헤더 */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
        </div>
        <Link
          href="/solutions/new"
          className="flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-lg transition-colors hover:bg-zinc-800"
          aria-label={t("newBtnAria")}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t("newBtn")}
        </Link>
      </div>

      {/* Hero card */}
      <div className="mb-8 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
            <Sparkles className="h-6 w-6 text-[var(--text-secondary)]" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">
              {t("heroTitle")}
            </h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">{t("heroDesc")}</p>
            <Link
              href="/solutions/new"
              className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            >
              {t("heroLink")}
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </div>

      {/* 최근 세션 */}
      <section aria-labelledby="recent-sessions-heading">
        <h2
          id="recent-sessions-heading"
          className="mb-4 text-sm font-semibold text-[var(--text-secondary)]"
        >
          {t("recentSessions")}
        </h2>

        {isLoading && (
          <div
            className="flex items-center justify-center py-12"
            role="status"
            aria-label={t("loadingAria")}
          >
            <Loader2 className="h-6 w-6 animate-spin text-zinc-700" />
            <span className="sr-only">{t("loadingAria")}</span>
          </div>
        )}

        {!isLoading && error && (
          <div
            role="alert"
            className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3"
          >
            <AlertCircle className="h-4 w-4 shrink-0 text-red-700" aria-hidden="true" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {!isLoading && !error && sessions.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-16 text-center">
            <Sparkles className="h-10 w-10 text-[var(--text-muted)]" aria-hidden="true" />
            <p className="mt-4 text-sm text-[var(--text-muted)]">{t("emptyState")}</p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">{t("emptyStateHint")}</p>
            <Link
              href="/solutions/new"
              className="mt-4 flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t("startBtn")}
            </Link>
          </div>
        )}

        {!isLoading && !error && sessions.length > 0 && (
          <ul className="space-y-2" role="list" aria-label={t("recentSessionsListAria")}>
            {sessions.map((s) => {
              const cfg = STATUS_CONFIG[s.status];
              const Icon = cfg.icon;
              const companyName = s.solution_prompt
                ? s.solution_prompt.slice(0, 40) + (s.solution_prompt.length > 40 ? "..." : "")
                : "—";
              const solutionRequest = s.solution_prompt ?? "";
              const createdAt = new Date(s.created_at).toLocaleDateString(
                "ko-KR",
                { year: "numeric", month: "short", day: "numeric" },
              );

              return (
                <li key={s.id}>
                  <Link
                    href={`/solutions/${s.id}`}
                    className="flex items-center gap-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-3 transition-colors hover:border-zinc-300 hover:bg-[var(--bg-hover)]"
                    aria-label={t("openSessionAria", { name: companyName })}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--bg-hover)]">
                      <Sparkles className="h-4 w-4 text-[var(--text-secondary)]" aria-hidden="true" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[var(--text-primary)]">
                        {companyName}
                      </p>
                      {solutionRequest && (
                        <p className="mt-0.5 truncate text-xs text-[var(--text-muted)]">
                          {solutionRequest.length > 80
                            ? solutionRequest.slice(0, 80) + "..."
                            : solutionRequest}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs text-[var(--text-muted)]">{createdAt}</span>
                      <div className="flex items-center gap-1.5">
                        <Icon
                          className={`h-3.5 w-3.5 ${cfg.className}`}
                          aria-hidden="true"
                        />
                        <span className="text-xs text-[var(--text-muted)]">
                          {tStatus(s.status)}
                        </span>
                      </div>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
