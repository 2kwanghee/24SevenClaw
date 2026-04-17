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
    <div className="rounded-xl border border-white/10 bg-white/[0.02]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-3.5 text-left"
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
          )}
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {title}
          </span>
          {badge !== undefined && (
            <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-xs text-slate-500">
              {badge}
            </span>
          )}
        </div>
      </button>
      {open && <div className="border-t border-white/10 px-5 py-4 space-y-4">{children}</div>}
    </div>
  );
}
