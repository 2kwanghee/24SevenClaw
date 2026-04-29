"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Building2, Users, Layers, Search, RefreshCw } from "lucide-react";
import { controlTower, type CustomerSummary } from "@/lib/api-client";

const STATUS_LABEL: Record<string, string> = {
  active: "운영 중",
  paused: "일시정지",
  archived: "종료",
};

const STATUS_COLOR: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  paused: "bg-yellow-100 text-yellow-700",
  archived: "bg-gray-100 text-gray-500",
};

export default function ControlTowerPage() {
  const { data: session } = useSession();
  const router = useRouter();

  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!session?.accessToken) return;
    setLoading(true);
    try {
      const res = await controlTower.listCustomers(session.accessToken as string, {
        search: search || undefined,
        status: statusFilter || undefined,
      });
      setCustomers(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, search, statusFilter]);

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Building2 className="h-6 w-6 text-indigo-600" />
          <div>
            <h1 className="text-xl font-semibold text-gray-900">컨트롤 타워</h1>
            <p className="text-sm text-gray-500">고객사별 프로젝트 현황을 관리합니다</p>
          </div>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
        >
          <RefreshCw className="h-4 w-4" />
          새로고침
        </button>
      </div>

      {/* 필터 */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="고객사 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">전체 상태</option>
          <option value="active">운영 중</option>
          <option value="paused">일시정지</option>
          <option value="archived">종료</option>
        </select>
      </div>

      {/* 집계 */}
      <p className="text-sm text-gray-500">총 {total}개 고객사</p>

      {/* 고객사 카드 그리드 */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      ) : customers.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-gray-200 py-16 text-gray-400">
          <Building2 className="h-10 w-10" />
          <p className="text-sm">고객사가 없습니다</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {customers.map((c) => (
            <button
              key={c.id}
              onClick={() => router.push(`/admin/control-tower/customers/${c.id}`)}
              className="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-5 text-left shadow-sm transition hover:border-indigo-300 hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Building2 className="h-5 w-5 flex-shrink-0 text-indigo-500" />
                  <span className="font-medium text-gray-900 line-clamp-1">
                    {c.company_name}
                  </span>
                </div>
                <span
                  className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                    STATUS_COLOR[c.customer_status] ?? "bg-gray-100 text-gray-500"
                  }`}
                >
                  {STATUS_LABEL[c.customer_status] ?? c.customer_status}
                </span>
              </div>

              <div className="flex gap-4 text-sm text-gray-500">
                <div className="flex items-center gap-1.5">
                  <Layers className="h-4 w-4" />
                  <span>프로젝트 {c.project_count}개</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Users className="h-4 w-4 text-blue-400" />
                  <span>진행 중 {c.active_session_count}건</span>
                </div>
              </div>

              {c.account_manager_name && (
                <p className="text-xs text-gray-400">
                  담당: {c.account_manager_name}
                </p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
