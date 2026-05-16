"use client";

import { CheckCircle2, Loader2, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

export type ValidationStatus = "idle" | "loading" | "valid" | "invalid";

interface IntegrationValidationBadgeProps {
  name: string;
  status: ValidationStatus;
  message: string;
}

export function IntegrationValidationBadge({
  name,
  status,
  message,
}: IntegrationValidationBadgeProps) {
  if (status === "idle") return null;

  return (
    <div
      role="status"
      className={cn(
        "flex items-center gap-2 rounded-lg px-3 py-2 text-xs",
        status === "loading" && "border border-zinc-200 bg-zinc-100 text-zinc-500",
        status === "valid" && "border border-emerald-200 bg-emerald-50 text-emerald-600",
        status === "invalid" && "border border-red-200 bg-red-50 text-red-600",
      )}
    >
      {status === "loading" && (
        <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" aria-hidden="true" />
      )}
      {status === "valid" && (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      )}
      {status === "invalid" && (
        <XCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      )}
      <span>
        <strong>{name}</strong> {message}
      </span>
    </div>
  );
}
