"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { TableCrud } from "@/components/admin/ops/table-crud";
import { useOpsTables } from "@/hooks/use-ops";

export default function AdminOpsTableDetailPage() {
  const t = useTranslations("ops.tables");
  const params = useParams<{ table: string }>();
  const tableKey = params.table;
  const { data } = useOpsTables();
  const info = data?.find((tb) => tb.key === tableKey);

  return (
    <RoleGuard roles={["superadmin"]}>
      <div className="space-y-6">
        <div>
          <Link
            href="/admin/ops/tables"
            className="mb-3 inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {t("backToList")}
          </Link>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">
            {info?.label ?? tableKey}
          </h1>
          <p className="mt-1 font-mono text-xs text-[var(--text-muted)]">
            {tableKey}
          </p>
        </div>

        <TableCrud tableKey={tableKey} />
      </div>
    </RoleGuard>
  );
}
