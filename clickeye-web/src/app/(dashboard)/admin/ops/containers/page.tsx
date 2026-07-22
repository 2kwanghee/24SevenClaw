"use client";

import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { ContainersTable } from "@/components/admin/ops/containers-table";

export default function AdminOpsContainersPage() {
  const t = useTranslations("ops.containers");

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
        <ContainersTable />
      </div>
    </RoleGuard>
  );
}
