"use client";

import { cn } from "@/lib/utils";
import type { MaturityLevel } from "@/lib/api-client";

const MATURITY_CONFIG: Record<
  MaturityLevel,
  { label: string; color: string; bg: string; ring: string }
> = {
  starter: {
    label: "Starter",
    color: "text-emerald-300",
    bg: "bg-emerald-500/15",
    ring: "ring-emerald-500/30",
  },
  intermediate: {
    label: "Intermediate",
    color: "text-blue-300",
    bg: "bg-blue-500/15",
    ring: "ring-blue-500/30",
  },
  advanced: {
    label: "Advanced",
    color: "text-amber-300",
    bg: "bg-amber-500/15",
    ring: "ring-amber-500/30",
  },
};

interface MaturityBadgeProps {
  level: MaturityLevel;
  className?: string;
}

export function MaturityBadge({ level, className }: MaturityBadgeProps) {
  const config = MATURITY_CONFIG[level];

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset",
        config.color,
        config.bg,
        config.ring,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
