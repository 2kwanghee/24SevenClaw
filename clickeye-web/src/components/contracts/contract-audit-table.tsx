"use client";

import { useCallback, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight, Filter, ScrollText } from "lucide-react";
import { useContractAuditLog } from "@/hooks/use-contracts";
import type { ContractAuditLogResponse } from "@/lib/api-client";

const PAGE_SIZE = 20;

const CHANGE_TYPE_LABELS: Record<string, string> = {
  create: "생성",
  update: "수정",
  delete: "삭제",
  apply: "적용",
  override: "오버라이드",
  sync: "동기화",
};

const CHANGE_TYPE_COLORS: Record<string, string> = {
  create: "bg-emerald-500/10 text-emerald-300",
  update: "bg-blue-500/10 text-blue-300",
  delete: "bg-red-500/10 text-red-300",
  apply: "bg-violet-500/10 text-violet-300",
  override: "bg-amber-500/10 text-amber-300",
  sync: "bg-cyan-500/10 text-cyan-300",
};

function AuditRow({ log }: { log: ContractAuditLogResponse }) {
  const changeLabel = CHANGE_TYPE_LABELS[log.change_type] ?? log.change_type;
  const changeColor =
    CHANGE_TYPE_COLORS[log.change_type] ?? "bg-slate-500/10 text-slate-300";

  const hasDiff = Object.keys(log.diff_snapshot).length > 0;

  return (
    <tr className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
      <td className="px-4 py-3 text-xs text-slate-500">
        {new Date(log.created_at).toLocaleString("ko-KR")}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium ${changeColor}`}
        >
          {changeLabel}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-300">
        <code className="rounded bg-white/[0.05] px-1.5 py-0.5 text-xs">
          {log.actor_id.slice(0, 8)}...
        </code>
      </td>
      <td className="px-4 py-3 text-sm text-slate-300">
        {log.contract_id ? (
          <code className="rounded bg-white/[0.05] px-1.5 py-0.5 text-xs">
            {log.contract_id.slice(0, 8)}...
          </code>
        ) : (
          <span className="text-xs text-slate-600">-</span>
        )}
      </td>
      <td className="max-w-xs px-4 py-3">
        {hasDiff ? (
          <pre className="max-h-20 overflow-auto rounded bg-white/[0.03] px-2 py-1 text-[10px] leading-relaxed text-slate-400">
            {JSON.stringify(log.diff_snapshot, null, 2)}
          </pre>
        ) : (
          <span className="text-xs text-slate-600">-</span>
        )}
      </td>
    </tr>
  );
}

interface ContractAuditTableProps {
  contractId?: string;
}

export function ContractAuditTable({ contractId }: ContractAuditTableProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const auditPage = Math.max(
    1,
    Number(searchParams.get("audit_page") ?? "1"),
  );
  const changeTypeFilter = searchParams.get("change_type") ?? "";

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

  const offset = (auditPage - 1) * PAGE_SIZE;

  const { data, isLoading, error } = useContractAuditLog({
    contract_id: contractId,
    change_type: changeTypeFilter || undefined,
    limit: PAGE_SIZE,
    offset,
  });

  const logs = data?.items;
  const hasMore = logs && logs.length === PAGE_SIZE;

  return (
    <div>
      {/* 헤더 + 필터 */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">계약 감사 로그</h3>
        <div className="relative">
          <button
            type="button"
            onClick={() => setFilterOpen(!filterOpen)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-violet-500/30 hover:bg-white/[0.05]"
          >
            <Filter className="h-3 w-3" />
            {changeTypeFilter
              ? CHANGE_TYPE_LABELS[changeTypeFilter] ?? changeTypeFilter
              : "전체"}
          </button>
          {filterOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setFilterOpen(false)}
              />
              <div className="absolute right-0 z-20 mt-1 w-36 rounded-xl border border-white/10 bg-slate-900 p-1 shadow-xl">
                <button
                  type="button"
                  onClick={() => {
                    updateParams({ change_type: "", audit_page: "" });
                    setFilterOpen(false);
                  }}
                  className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                    !changeTypeFilter
                      ? "bg-violet-500/10 text-violet-300"
                      : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                  }`}
                >
                  전체
                </button>
                {Object.entries(CHANGE_TYPE_LABELS).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => {
                      updateParams({ change_type: value, audit_page: "" });
                      setFilterOpen(false);
                    }}
                    className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                      changeTypeFilter === value
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
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-10 animate-pulse rounded-lg bg-white/[0.03]"
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
      {logs && logs.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-white/5 bg-white/[0.02]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.03]">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  시각
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  유형
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  수행자
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  계약 ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  변경 내용
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
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <ScrollText className="h-10 w-10 text-slate-600" />
          <p className="text-sm text-slate-400">감사 로그가 없습니다</p>
        </div>
      )}

      {/* 페이지네이션 */}
      {logs && logs.length > 0 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <button
            type="button"
            disabled={auditPage <= 1}
            onClick={() =>
              updateParams({ audit_page: String(auditPage - 1) })
            }
            aria-label="이전 페이지"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-slate-400 transition-colors hover:border-violet-500/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs text-slate-400">{auditPage} 페이지</span>
          <button
            type="button"
            disabled={!hasMore}
            onClick={() =>
              updateParams({ audit_page: String(auditPage + 1) })
            }
            aria-label="다음 페이지"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-slate-400 transition-colors hover:border-violet-500/30 hover:text-white disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
