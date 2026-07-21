"use client";

import { useState, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

interface ConfirmByTypingDialogProps {
  /** 다이얼로그 열림 여부 */
  open: boolean;
  /** 제목 (caller가 i18n으로 전달) */
  title: string;
  /** 본문 설명 */
  description?: ReactNode;
  /** 확인을 위해 사용자가 정확히 입력해야 하는 문구 */
  confirmPhrase: string;
  /** 확인 버튼 라벨 (기본: 공통 "삭제") */
  confirmLabel?: string;
  /** 처리 중 상태 */
  isPending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 위험 작업(삭제 등)을 특정 문구 입력으로 재확인시키는 범용 다이얼로그.
 * reset-project-dialog의 type-to-confirm 패턴을 일반화한 것.
 */
export function ConfirmByTypingDialog({
  open,
  title,
  description,
  confirmPhrase,
  confirmLabel,
  isPending = false,
  onConfirm,
  onCancel,
}: ConfirmByTypingDialogProps) {
  const t = useTranslations("common.confirmByTyping");
  const [value, setValue] = useState("");

  if (!open) return null;

  const isEnabled = value === confirmPhrase && !isPending;

  function close() {
    setValue("");
    onCancel();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={close}
        onKeyDown={(e) => e.key === "Escape" && close()}
        role="button"
        tabIndex={0}
        aria-label={t("close")}
      />

      <div className="relative mx-4 w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-2xl shadow-black/10">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-50">
          <AlertTriangle className="h-6 w-6 text-amber-700" />
        </div>

        <h3 className="mt-4 text-lg font-semibold text-[var(--text-primary)]">
          {title}
        </h3>
        {description && (
          <div className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
            {description}
          </div>
        )}

        <div className="mt-4">
          <label
            htmlFor="confirm-by-typing-input"
            className="mb-1.5 block text-xs text-[var(--text-muted)]"
          >
            {t("prompt")}{" "}
            <strong className="text-[var(--text-secondary)]">
              {confirmPhrase}
            </strong>
          </label>
          <input
            id="confirm-by-typing-input"
            type="text"
            value={value}
            autoFocus
            onChange={(e) => setValue(e.target.value)}
            placeholder={confirmPhrase}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-200"
          />
        </div>

        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={close}
            className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            {t("cancel")}
          </button>
          <button
            type="button"
            onClick={() => {
              setValue("");
              onConfirm();
            }}
            disabled={!isEnabled}
            className="flex-1 rounded-xl bg-red-600 py-2.5 text-sm font-medium text-white shadow-lg shadow-red-600/25 transition-all hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isPending ? t("pending") : (confirmLabel ?? t("confirm"))}
          </button>
        </div>
      </div>
    </div>
  );
}
