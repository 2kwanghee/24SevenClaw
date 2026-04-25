"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

const SIZE_CLASS = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
} as const;

interface BaseModalProps {
  open: boolean;
  onClose?: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  /** 모달 최대 너비 (기본값: "md") */
  size?: keyof typeof SIZE_CLASS;
  /** 스크롤바를 시각적으로 숨길지 여부 */
  hideScrollbar?: boolean;
  /** 모달 컨테이너에 추가할 클래스 */
  className?: string;
  /** aria-labelledby 연결용 id */
  titleId?: string;
}

/**
 * 공통 모달 래퍼 컴포넌트.
 *
 * - ESC 키 · 백드롭 클릭으로 닫기 (onClose 제공 시)
 * - hideScrollbar=true 시 스크롤은 동작하되 스크롤바가 숨겨짐
 * - size prop으로 max-w-* 제어
 */
export function BaseModal({
  open,
  onClose,
  title,
  children,
  size = "md",
  hideScrollbar = false,
  className,
  titleId,
}: BaseModalProps) {
  useEffect(() => {
    if (!open || !onClose) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm"
      role="presentation"
      onClick={onClose}
    >
      <div
        className={cn(
          "flex w-full flex-col rounded-2xl bg-[var(--bg-surface)] shadow-2xl",
          SIZE_CLASS[size],
          className,
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        {(title || onClose) && (
          <div className="flex shrink-0 items-center justify-between border-b border-[var(--border-subtle)] px-6 py-4">
            {title ? (
              <div
                id={titleId}
                className="text-base font-semibold text-[var(--text-primary)]"
              >
                {title}
              </div>
            ) : (
              <div />
            )}
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="닫기"
                className="rounded-md p-1 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>
        )}
        <div
          className={cn(
            "overflow-y-auto",
            hideScrollbar && "setup-guide-scroll",
          )}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
