"use client";

import Link from "next/link";
import { ChevronRight, Database, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { useOpsTables } from "@/hooks/use-ops";

export default function AdminOpsTablesPage() {
  const t = useTranslations("ops.tables");
  const { data, isLoading, isError } = useOpsTables();

  return (
    <RoleGuard roles={["superadmin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">
            {t("pageTitle")}
          </h1>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            {t("pageDescription")}
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" />
          </div>
        ) : isError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 py-6 text-center text-sm text-red-700">
            {t("listError")}
          </div>
        ) : (data ?? []).length === 0 ? (
          <div className="rounded-xl border border-dashed border-[var(--border-subtle)] py-8 text-center text-sm text-[var(--text-muted)]">
            {t("listEmpty")}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(data ?? []).map((tb) => (
              <Link
                key={tb.key}
                href={`/admin/ops/tables/${tb.key}`}
                className="group flex items-center justify-between gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 transition-all hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)]"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 shrink-0 text-[var(--text-muted)]" />
                    <span className="truncate text-sm font-medium text-[var(--text-primary)]">
                      {tb.label}
                    </span>
                  </div>
                  <p className="mt-1 truncate font-mono text-[11px] text-[var(--text-muted)]">
                    {tb.key}
                    {typeof tb.row_count === "number"
                      ? ` · ${t("rowCount", { count: tb.row_count })}`
                      : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {tb.ops.map((op) => (
                      <span
                        key={op}
                        className="inline-flex items-center rounded border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-1.5 py-0.5 text-[10px] font-medium uppercase text-[var(--text-muted)]"
                      >
                        {op}
                      </span>
                    ))}
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-[var(--text-muted)] transition-transform group-hover:translate-x-0.5" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </RoleGuard>
  );
}
