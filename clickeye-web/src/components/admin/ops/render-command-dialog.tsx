"use client";

import { useState } from "react";
import { Copy, Check, Terminal, X } from "lucide-react";
import { useTranslations } from "next-intl";

import type { OpsEnvRenderResponse } from "@/lib/api-client";

interface RenderCommandDialogProps {
  open: boolean;
  result: OpsEnvRenderResponse | null;
  onClose: () => void;
}

/**
 * env "적용" 결과로 반환된 재생성 명령을 표시한다.
 * 서버는 docker를 실행하지 않으며, 운영자가 이 명령을 수동 실행해야 한다.
 */
export function RenderCommandDialog({
  open,
  result,
  onClose,
}: RenderCommandDialogProps) {
  const t = useTranslations("ops.env.render");
  const [copied, setCopied] = useState(false);

  if (!open || !result) return null;

  async function copy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* 클립보드 접근 불가 시 무시 (사용자가 수동 선택 복사) */
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={t("title")}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        role="button"
        tabIndex={0}
        aria-label={t("close")}
      />

      <div className="relative mx-4 w-full max-w-lg rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-2xl shadow-black/10">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
              <Terminal className="h-5 w-5 text-[var(--text-secondary)]" />
            </div>
            <h3 className="text-base font-semibold text-[var(--text-primary)]">
              {t("title")}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("close")}
            className="rounded-lg p-1 text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-800">
          {t("manualNotice")}
        </p>

        <div className="mt-4">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-medium text-[var(--text-muted)]">
              {t("command")}
            </span>
            <button
              type="button"
              onClick={copy}
              className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
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
          <pre className="max-h-48 overflow-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-3 text-xs text-[var(--text-primary)]">
            <code>{result.command}</code>
          </pre>
        </div>

        <dl className="mt-4 space-y-1.5 text-xs">
          <div className="flex gap-2">
            <dt className="w-28 shrink-0 text-[var(--text-muted)]">
              {t("renderedPath")}
            </dt>
            <dd className="break-all font-mono text-[var(--text-secondary)]">
              {result.rendered_path}
            </dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-28 shrink-0 text-[var(--text-muted)]">
              {t("appliedKeys")}
            </dt>
            <dd className="text-[var(--text-secondary)]">
              {result.applied_keys.length > 0
                ? result.applied_keys.join(", ")
                : "-"}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
