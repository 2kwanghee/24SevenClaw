"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: string | number;
}

export function CollapsibleSection({
  title,
  defaultOpen = true,
  children,
  badge,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-3.5 text-left"
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-[var(--text-muted)]" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-[var(--text-muted)]" />
          )}
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            {title}
          </span>
          {badge !== undefined && (
            <span className="rounded-full bg-[var(--bg-hover)] px-1.5 py-0.5 text-xs text-[var(--text-muted)]">
              {badge}
            </span>
          )}
        </div>
      </button>
      {open && <div className="border-t border-[var(--border-subtle)] px-5 py-4 space-y-4">{children}</div>}
    </div>
  );
}
