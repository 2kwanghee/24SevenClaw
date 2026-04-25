"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Building2,
  ChevronLeft,
  Layers,
  PlayCircle,
  ArrowRight,
  Pause,
  Play,
  Archive,
} from "lucide-react";
import {
  controlTower,
  type CustomerDetail,
  type CtProjectOverview,
} from "@/lib/api-client";

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

export default function CustomerDetailPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const { data: session } = useSession();
  const router = useRouter();

  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [projects, setProjects] = useState<CtProjectOverview[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(false);

  async function load() {
    if (!session?.accessToken || !orgId) return;
    setLoading(true);
    try {
      const [custData, projData] = await Promise.all([
        controlTower.getCustomer(session.accessToken as string, orgId),
        controlTower.listCustomerProjects(session.accessToken as string, orgId),
      ]);
      setCustomer(custData);
      setProjects(projData.items);
      setTotal(projData.total);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, orgId]);

  async function handleStatusChange(newStatus: string) {
    if (!session?.accessToken || !orgId) return;
    setStatusLoading(true);
    try {
      const updated = await controlTower.setCustomerStatus(
        session.accessToken as string,
        orgId,
        newStatus,
      );
      setCustomer(updated);
    } finally {
      setStatusLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="h-32 animate-pulse rounded-xl bg-gray-100" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-gray-100" />
          ))}
        </div>
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="flex items-center justify-center p-16 text-gray-400">
        고객사를 찾을 수 없습니다
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* 뒤로가기 + 헤더 */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => router.push("/admin/control-tower")}
          className="mt-0.5 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ChevronLeft className="h-4 w-4" />
          컨트롤 타워
        </button>
      </div>

      {/* 고객사 정보 카드 */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="h-7 w-7 text-indigo-500" />
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                {customer.company_name}
              </h1>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                {customer.industry && <span>{customer.industry}</span>}
                {customer.size && <span>· {customer.size}명</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-sm font-medium ${
                STATUS_COLOR[customer.customer_status] ?? "bg-gray-100 text-gray-500"
              }`}
            >
              {STATUS_LABEL[customer.customer_status] ?? customer.customer_status}
            </span>

            {/* 상태 변경 버튼 */}
            {customer.customer_status === "active" && (
              <button
                disabled={statusLoading}
                onClick={() => handleStatusChange("paused")}
                className="flex items-center gap-1.5 rounded-lg border border-yellow-200 px-3 py-1.5 text-sm text-yellow-700 hover:bg-yellow-50 disabled:opacity-50"
              >
                <Pause className="h-3.5 w-3.5" />
                일시정지
              </button>
            )}
            {customer.customer_status === "paused" && (
              <button
                disabled={statusLoading}
                onClick={() => handleStatusChange("active")}
                className="flex items-center gap-1.5 rounded-lg border border-green-200 px-3 py-1.5 text-sm text-green-700 hover:bg-green-50 disabled:opacity-50"
              >
                <Play className="h-3.5 w-3.5" />
                재개
              </button>
            )}
            {customer.customer_status !== "archived" && (
              <button
                disabled={statusLoading}
                onClick={() => handleStatusChange("archived")}
                className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-50 disabled:opacity-50"
              >
                <Archive className="h-3.5 w-3.5" />
                종료
              </button>
            )}
          </div>
        </div>

        {customer.company_description && (
          <p className="mt-4 text-sm text-gray-600">{customer.company_description}</p>
        )}

        <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-500">
          {customer.main_product && (
            <span>주요 제품: {customer.main_product}</span>
          )}
          {customer.account_manager_name && (
            <span>담당 PM: {customer.account_manager_name}</span>
          )}
        </div>
      </div>

      {/* 프로젝트 목록 */}
      <div>
        <h2 className="mb-3 text-base font-medium text-gray-700">
          프로젝트 ({total}개)
        </h2>

        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-gray-200 py-12 text-gray-400">
            <Layers className="h-8 w-8" />
            <p className="text-sm">등록된 프로젝트가 없습니다</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {projects.map((proj) => (
              <button
                key={proj.id}
                onClick={() =>
                  router.push(`/projects/${proj.id}/ai-team`)
                }
                className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-5 py-4 text-left shadow-sm transition hover:border-indigo-300 hover:shadow-md"
              >
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{proj.name}</span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                      {proj.project_type ?? "legacy"}
                    </span>
                  </div>
                  <div className="flex gap-3 text-sm text-gray-500">
                    <div className="flex items-center gap-1">
                      <Layers className="h-3.5 w-3.5" />
                      <span>세션 {proj.session_count}개</span>
                    </div>
                    {proj.active_session_count > 0 && (
                      <div className="flex items-center gap-1 text-blue-500">
                        <PlayCircle className="h-3.5 w-3.5" />
                        <span>진행 중 {proj.active_session_count}건</span>
                      </div>
                    )}
                    {proj.owner_name && (
                      <span className="text-gray-400">소유: {proj.owner_name}</span>
                    )}
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 flex-shrink-0 text-gray-400" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
