"use client";

import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";

interface ConfirmDialogProps {
  /** 다이얼로그 열림 여부 */
  open: boolean;
  /** 제목 (caller가 i18n으로 전달) */
  title: string;
  /** 본문 설명 */
  description?: ReactNode;
  /** 확인 버튼 라벨 (기본: 공통 "확인") */
  confirmLabel?: string;
  /** 위험 강조 색상 톤 */
  tone?: "danger" | "warning";
  /** 처리 중 상태 */
  isPending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 위험 작업(비활성화 등)을 단순 확인시키는 범용 다이얼로그.
 * type-to-confirm이 필요하면 ConfirmByTypingDialog를 사용한다.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  tone = "danger",
  isPending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const tC = useTranslations("common");

  if (!open) return null;

  const isDanger = tone === "danger";
  const iconWrapCls = isDanger ? "bg-red-50" : "bg-amber-50";
  const iconCls = isDanger ? "text-red-700" : "text-amber-700";
  const confirmBtnCls = isDanger
    ? "bg-red-600 shadow-red-600/25 hover:bg-red-500"
    : "bg-amber-600 shadow-amber-600/25 hover:bg-amber-500";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
        onKeyDown={(e) => e.key === "Escape" && onCancel()}
        role="button"
        tabIndex={0}
        aria-label={tC("aria.close")}
      />

      <div className="relative mx-4 w-full max-w-sm rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-2xl shadow-black/10">
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${iconWrapCls}`}>
          <AlertTriangle className={`h-6 w-6 ${iconCls}`} />
        </div>

        <h3 className="mt-4 text-lg font-semibold text-[var(--text-primary)]">
          {title}
        </h3>
        {description && (
          <div className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
            {description}
          </div>
        )}

        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            {tC("actions.cancel")}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className={`flex-1 rounded-xl py-2.5 text-sm font-medium text-white shadow-lg transition-all disabled:cursor-not-allowed disabled:opacity-50 ${confirmBtnCls}`}
          >
            {isPending ? tC("actions.processing") : (confirmLabel ?? tC("actions.confirm"))}
          </button>
        </div>
      </div>
    </div>
  );
}
