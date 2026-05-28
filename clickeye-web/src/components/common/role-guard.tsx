"use client";

import { useEffect, type ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";

import { usePermissions } from "@/hooks/use-rbac";
import { useRBACStore } from "@/stores/rbac-store";
import type { SystemRole } from "@/lib/api-client";

interface RoleGuardProps {
  children: ReactNode;
  /** 허용할 시스템 역할 목록 */
  roles?: SystemRole[];
  /** 필요한 권한 (하나라도 있으면 통과) */
  permissions?: string[];
  /** 권한 부족 시 표시할 대체 UI (기본: 접근 거부 메시지) */
  fallback?: ReactNode;
}

export function RoleGuard({
  children,
  roles,
  permissions: requiredPermissions,
  fallback,
}: RoleGuardProps) {
  const { data, isLoading } = usePermissions();
  const setPermissions = useRBACStore((s) => s.setPermissions);

  // 권한 데이터를 스토어에 동기화
  useEffect(() => {
    if (data) {
      setPermissions(data.permissions, data.system_role);
    }
  }, [data, setPermissions]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
      </div>
    );
  }

  if (!data) return null;

  // 역할 검사
  if (roles && !roles.includes(data.system_role)) {
    return fallback ?? <AccessDenied />;
  }

  // 권한 검사 (하나라도 충족하면 통과)
  if (
    requiredPermissions &&
    !requiredPermissions.some((p) => data.permissions.includes(p))
  ) {
    return fallback ?? <AccessDenied />;
  }

  return <>{children}</>;
}

function AccessDenied() {
  const t = useTranslations("common.roleGuard");
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-50">
        <ShieldAlert className="h-8 w-8 text-red-700" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          {t("description")}
        </p>
      </div>
    </div>
  );
}
