"use client";

import { useState } from "react";
import {
  Loader2,
  PlayCircle,
  Copy,
  Check,
  AlertTriangle,
  Webhook,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useOpsWebhookStatus, useRenderOpsWebhook } from "@/hooks/use-ops";
import type { OpsWebhookRenderResult } from "@/lib/api-client";

export function WebhookEnvCard() {
  const t = useTranslations("ops.webhook");
  const { data, isLoading, isError } = useOpsWebhookStatus();
  const renderMut = useRenderOpsWebhook();

  const [result, setResult] = useState<OpsWebhookRenderResult | null>(null);
  const [copied, setCopied] = useState(false);

  // 렌더 이후에는 렌더 결과의 legacy_present 가 최신이고, 그 전에는 status 값을 쓴다.
  const legacyPresent = result?.legacy_present ?? data?.legacy_present ?? false;

  // projects 는 Linear 자격증명이 등록된 전 프로젝트(has_secret=false 포함)라,
  // 실제 MAP 대상은 시크릿 보유 프로젝트만이다.
  const withSecret = data?.projects.filter((p) => p.has_secret).length ?? 0;
  const totalProjects = data?.projects.length ?? 0;

  async function handleRender() {
    try {
      const res = await renderMut.mutateAsync();
      setResult(res);
    } catch {
      toast.error(t("error"));
    }
  }

  async function copyCommand() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.restart_command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* 클립보드 접근 불가 시 무시 (사용자가 수동 선택 복사) */
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--bg-hover)]">
            <Webhook className="h-4.5 w-4.5 text-[var(--text-secondary)]" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              {t("title")}
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              {t("description")}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleRender}
          disabled={renderMut.isPending || isLoading || isError}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-[var(--accent-fg)] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {renderMut.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <PlayCircle className="h-3.5 w-3.5" />
          )}
          {t("renderButton")}
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" />
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 py-4 text-center text-sm text-red-700">
          {t("statusError")}
        </div>
      ) : data ? (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2">
            <dt className="text-[11px] text-[var(--text-muted)]">
              {t("projectCount")}
            </dt>
            <dd className="mt-0.5 text-sm font-semibold text-[var(--text-primary)]">
              {t("projectCountValue", {
                withSecret,
                total: totalProjects,
              })}
            </dd>
            <dd className="text-[10px] text-[var(--text-muted)]">
              {t("projectCountHint")}
            </dd>
          </div>
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2">
            <dt className="text-[11px] text-[var(--text-muted)]">
              {t("fileState")}
            </dt>
            <dd className="mt-0.5 text-sm font-medium text-[var(--text-primary)]">
              {data.file_exists ? t("fileExists") : t("fileMissing")}
            </dd>
          </div>
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2">
            <dt className="text-[11px] text-[var(--text-muted)]">
              {t("mapLine")}
            </dt>
            <dd className="mt-0.5 text-sm font-medium text-[var(--text-primary)]">
              {data.map_line_present ? t("mapPresent") : t("mapAbsent")}
            </dd>
          </div>
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2">
            <dt className="text-[11px] text-[var(--text-muted)]">
              {t("renderedPath")}
            </dt>
            <dd className="mt-0.5 break-all font-mono text-xs text-[var(--text-secondary)]">
              {data.rendered_path}
            </dd>
          </div>
        </dl>
      ) : null}

      {legacyPresent && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-relaxed text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{t("legacyWarning")}</span>
        </div>
      )}

      {result && (
        <div className="space-y-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-4">
          <div className="flex flex-wrap gap-x-6 gap-y-1.5 text-xs">
            <div className="flex gap-1.5">
              <span className="text-[var(--text-muted)]">
                {t("entryCount")}
              </span>
              <span className="font-semibold text-[var(--text-primary)]">
                {result.entry_count}
              </span>
            </div>
            <div className="flex gap-1.5">
              <span className="text-[var(--text-muted)]">
                {t("renderedPath")}
              </span>
              <span className="break-all font-mono text-[var(--text-secondary)]">
                {result.rendered_path}
              </span>
            </div>
          </div>

          {result.skipped.length > 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50/70 px-3 py-2">
              <p className="text-[11px] font-medium text-amber-800">
                {t("skippedTitle", { count: result.skipped.length })}
              </p>
              <ul className="mt-1 space-y-0.5 text-[11px] text-amber-700">
                {result.skipped.map((s) => (
                  <li key={s.project_id} className="break-all">
                    <span className="font-mono">{s.team_id}</span>
                    {" · "}
                    {s.project_name} — {s.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[11px] font-medium text-[var(--text-muted)]">
                {t("restartCommand")}
              </span>
              <button
                type="button"
                onClick={copyCommand}
                className="flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-green-600" />
                    {t("copied")}
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    {t("copy")}
                  </>
                )}
              </button>
            </div>
            <pre className="max-h-40 overflow-auto rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 text-xs text-[var(--text-primary)]">
              <code>{result.restart_command}</code>
            </pre>
            <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-relaxed text-amber-800">
              {t("restartNotice")}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
