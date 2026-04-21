"use client";

import { Suspense, useCallback, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import {
  ScrollText,
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react";

import { RoleGuard } from "@/components/common/role-guard";
import { useAuditLog } from "@/hooks/use-rbac";
import type { AuditLogResponse } from "@/lib/api-client";

const PAGE_SIZE = 20;

const ACTION_LABELS: Record<string, string> = {
  assign_system_role: "역할 변경",
  add_org_member: "멤버 추가",
  remove_org_member: "멤버 제거",
};

const ACTION_COLORS: Record<string, string> = {
  assign_system_role: "bg-violet-500/10 text-violet-300",
  add_org_member: "bg-emerald-500/10 text-emerald-300",
  remove_org_member: "bg-red-500/10 text-red-300",
};

function AuditRow({ log }: { log: AuditLogResponse }) {
  const actionLabel = ACTION_LABELS[log.action] ?? log.action;
  const actionColor =
    ACTION_COLORS[log.action] ?? "bg-slate-500/10 text-slate-300";

  return (
    <tr className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
      <td className="px-4 py-3 text-xs text-slate-500">
        {new Date(log.created_at).toLocaleString("ko-KR")}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium ${actionColor}`}
        >
          {actionLabel}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-300">
        <code className="rounded bg-white/[0.05] px-1.5 py-0.5 text-xs">
          {log.actor_id.slice(0, 8)}...
        </code>
      </td>
      <td className="px-4 py-3 text-sm text-slate-300">
        {log.target_user_id ? (
          <code className="rounded bg-white/[0.05] px-1.5 py-0.5 text-xs">
            {log.target_user_id.slice(0, 8)}...
          </code>
        ) : (
          <span className="text-xs text-slate-600">-</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 text-xs">
          {log.old_value && (
            <span className="rounded bg-red-500/10 px-1.5 py-0.5 text-red-400 line-through">
              {log.old_value}
            </span>
          )}
          {log.old_value && <span className="text-slate-600">&rarr;</span>}
          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-emerald-300">
            {log.new_value}
          </span>
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {log.resource ?? "-"}
      </td>
    </tr>
  );
}

function AuditContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const currentPage = Math.max(1, Number(searchParams.get("page") ?? "1"));
  const actionFilter = searchParams.get("action") ?? "";

  const [filterOpen, setFilterOpen] = useState(false);

  const updateParams = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value) {
          params.set(key, value);
        } else {
          params.delete(key);
        }
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname],
  );

  const offset = (currentPage - 1) * PAGE_SIZE;

  const { data: logs, isLoading, error } = useAuditLog({
    action: actionFilter || undefined,
    limit: PAGE_SIZE,
    offset,
  });

  const hasMore = logs && logs.length === PAGE_SIZE;

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10">
            <ScrollText className="h-5 w-5 text-violet-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">감사 로그</h1>
            <p className="mt-0.5 text-sm text-slate-400">
              역할 및 권한 변경 이력을 확인합니다
            </p>
          </div>
        </div>

        {/* 액션 필터 */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setFilterOpen(!filterOpen)}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-slate-300 transition-colors hover:border-violet-500/30 hover:bg-white/[0.05]"
          >
            <Filter className="h-4 w-4" />
            {actionFilter
              ? ACTION_LABELS[actionFilter] ?? actionFilter
              : "모든 액션"}
          </button>

          {filterOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setFilterOpen(false)}
              />
              <div className="absolute right-0 z-20 mt-1 w-48 rounded-xl border border-white/10 bg-slate-900 p-1 shadow-xl">
                <button
                  type="button"
                  onClick={() => {
                    updateParams({ action: "", page: "" });
                    setFilterOpen(false);
                  }}
                  className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                    !actionFilter
                      ? "bg-violet-500/10 text-violet-300"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  }`}
                >
                  모든 액션
                </button>
                {Object.entries(ACTION_LABELS).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => {
                      updateParams({ action: value, page: "" });
                      setFilterOpen(false);
                    }}
                    className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                      actionFilter === value
                        ? "bg-violet-500/10 text-violet-300"
                        : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-12 animate-pulse rounded-xl bg-white/[0.03]"
            />
          ))}
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">
          감사 로그를 불러오지 못했습니다.
        </div>
      )}

      {/* 테이블 */}
      {logs && (
        <div className="overflow-x-auto rounded-xl border border-white/5 bg-white/[0.02]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.03]">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  시각
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  액션
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  수행자
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  대상
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  변경 내용
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  리소스
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <AuditRow key={log.id} log={log} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 빈 상태 */}
      {logs && logs.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <ScrollText className="h-12 w-12 text-slate-600" />
          <p className="text-sm text-slate-400">감사 로그가 없습니다</p>
        </div>
      )}

      {/* 페이지네이션 */}
      {logs && logs.length > 0 && (
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => updateParams({ page: String(currentPage - 1) })}
            aria-label="이전 페이지"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-slate-400 transition-colors hover:border-violet-500/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          <span className="text-sm text-slate-400">
            {currentPage} 페이지
          </span>

          <button
            type="button"
            disabled={!hasMore}
            onClick={() => updateParams({ page: String(currentPage + 1) })}
            aria-label="다음 페이지"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-slate-400 transition-colors hover:border-violet-500/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}

export default function AdminAuditPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <Suspense
        fallback={
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="h-12 animate-pulse rounded-xl bg-white/[0.03]"
              />
            ))}
          </div>
        }
      >
        <AuditContent />
      </Suspense>
    </RoleGuard>
  );
}
