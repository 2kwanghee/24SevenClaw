"use client";

import { FlaskConical } from "lucide-react";

import { useMockMode } from "@/stores/mock-mode-store";

/**
 * 딜리버리 콘솔 목업(샘플) 데이터 표시 토글.
 * ON 시 앰버 톤으로 강조하여 실데이터가 아님을 시각적으로 알린다.
 */
export function MockModeToggle() {
  const enabled = useMockMode((s) => s.enabled);
  const toggle = useMockMode((s) => s.toggle);

  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      aria-label="목업 데이터 표시"
      onClick={toggle}
      className={`inline-flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
        enabled
          ? "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
          : "border-[var(--border-medium)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
      }`}
    >
      <FlaskConical className="h-3.5 w-3.5" aria-hidden="true" />
      목업 데이터
      <span
        className={`relative inline-flex h-4 w-7 flex-none items-center rounded-full transition-colors ${
          enabled ? "bg-amber-500" : "bg-[var(--border-medium)]"
        }`}
        aria-hidden="true"
      >
        <span
          className={`inline-block h-3 w-3 transform rounded-full bg-white shadow transition-transform ${
            enabled ? "translate-x-3.5" : "translate-x-0.5"
          }`}
        />
      </span>
    </button>
  );
}
