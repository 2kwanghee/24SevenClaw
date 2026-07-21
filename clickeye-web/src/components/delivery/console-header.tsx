"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { ArrowLeft, GitBranch, KeyRound } from "lucide-react";

import type { KeyStatus, ProjectResponse } from "@/lib/api-client";

const KEY_STATUS_CLS: Record<KeyStatus, string> = {
  fresh:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  stale:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
  no_saved_key:
    "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
  never_downloaded:
    "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
  "n/a": "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
};

function KeyBadge({ name, status }: { name: string; status: KeyStatus }) {
  const t = useTranslations("delivery");
  const cls = KEY_STATUS_CLS[status] ?? KEY_STATUS_CLS["n/a"];
  const label = t(`keyStatus.${status in KEY_STATUS_CLS ? status : "n/a"}`);
  return (
    <span
      className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-medium ${cls}`}
    >
      <KeyRound className="h-3 w-3" aria-hidden="true" />
      {name}
      <b className="font-semibold">{label}</b>
    </span>
  );
}

interface ConsoleHeaderProps {
  engagementName: string;
  phase?: string;
  project?: ProjectResponse;
  onSync: () => void;
  syncing: boolean;
}

export function ConsoleHeader({
  engagementName,
  phase,
  project,
  onSync,
  syncing,
}: ConsoleHeaderProps) {
  const t = useTranslations("delivery");
  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 shadow-[0_1px_2px_rgba(20,24,33,0.05)] sm:p-6">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <Link
            href="/delivery"
            className="mt-0.5 rounded-lg p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            aria-label={t("console.backToList")}
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          </Link>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
                {engagementName}
              </h1>
              {phase && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-current"
                    aria-hidden="true"
                  />
                  {t.has(`phase.${phase}`) ? t(`phase.${phase}`) : phase}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              {t("console.subtitle")}
            </p>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {project && (
            <>
              <KeyBadge name="Anthropic" status={project.anthropic_key_status} />
              <KeyBadge name="Linear" status={project.linear_key_status} />
            </>
          )}
          <button
            type="button"
            onClick={onSync}
            disabled={syncing}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--border-medium)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-semibold text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-50"
          >
            <GitBranch
              className={`h-3.5 w-3.5 ${syncing ? "animate-pulse" : ""}`}
              aria-hidden="true"
            />
            {t("console.syncLinear")}
          </button>
        </div>
      </div>
    </section>
  );
}
