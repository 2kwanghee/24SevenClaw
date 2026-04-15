"use client";

import { useEffect, type ReactNode } from "react";
import { ShieldAlert } from "lucide-react";

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
  const store = useRBACStore();

  // 권한 데이터를 스토어에 동기화
  useEffect(() => {
    if (data) {
      store.setPermissions(data.permissions, data.system_role);
    }
  }, [data, store]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
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
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10">
        <ShieldAlert className="h-8 w-8 text-red-400" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-slate-200">
          접근 권한이 없습니다
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          이 페이지에 접근하려면 관리자 권한이 필요합니다.
        </p>
      </div>
    </div>
  );
}
