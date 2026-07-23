"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import {
  Building2,
  ChevronLeft,
  Layers,
  PlayCircle,
  ArrowRight,
  Pause,
  Play,
  Archive,
  Trash2,
} from "lucide-react";
import {
  apiClient,
  controlTower,
  type CustomerDetail,
  type CtProjectOverview,
} from "@/lib/api-client";
import { DeleteProjectDialog } from "@/components/projects/delete-project-dialog";
import { useMe } from "@/hooks/use-me";

const STATUS_LABEL: Record<string, string> = {
  active: "운영 중",
  paused: "일시정지",
  archived: "종료",
};

const STATUS_COLOR: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  paused: "bg-yellow-100 text-yellow-700",
  archived: "bg-[var(--bg-base)] text-[var(--text-muted)]",
};

export default function CustomerDetailPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const { data: session } = useSession();
  const { data: me } = useMe();
  const router = useRouter();

  const isSuperadmin = me?.system_role === "superadmin";

  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [projects, setProjects] = useState<CtProjectOverview[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(false);
  const [featureLoading, setFeatureLoading] = useState(false);
  // 프로젝트 삭제 (superadmin 전용)
  const [deleteTarget, setDeleteTarget] = useState<CtProjectOverview | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleDeleteProject() {
    if (!session?.accessToken || !deleteTarget) return;
    setDeleting(true);
    try {
      await apiClient.projects.delete(session.accessToken as string, deleteTarget.id);
      toast.success("프로젝트를 삭제했습니다");
      setDeleteTarget(null);
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "프로젝트 삭제에 실패했습니다");
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

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

  async function handleFeatureToggle(featureName: string, current: boolean) {
    if (!session?.accessToken || !orgId) return;
    setFeatureLoading(true);
    try {
      const updated = await controlTower.setOrgFeature(
        session.accessToken as string,
        orgId,
        featureName,
        !current,
      );
      setCustomer(updated);
    } finally {
      setFeatureLoading(false);
    }
  }

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
        <div className="h-32 animate-pulse rounded-xl bg-[var(--bg-base)]" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-[var(--bg-base)]" />
          ))}
        </div>
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="flex items-center justify-center p-16 text-[var(--text-muted)]">
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
          className="mt-0.5 flex items-center gap-1 text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
        >
          <ChevronLeft className="h-4 w-4" />
          컨트롤 타워
        </button>
      </div>

      {/* 고객사 정보 카드 */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="h-7 w-7 text-[var(--accent)]" />
            <div>
              <h1 className="text-xl font-semibold text-[var(--text-primary)]">
                {customer.company_name}
              </h1>
              <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                {customer.industry && <span>{customer.industry}</span>}
                {customer.size && <span>· {customer.size}명</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-sm font-medium ${
                STATUS_COLOR[customer.customer_status] ?? "bg-[var(--bg-base)] text-[var(--text-muted)]"
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
                className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-sm text-[var(--text-muted)] hover:bg-[var(--bg-hover)] disabled:opacity-50"
              >
                <Archive className="h-3.5 w-3.5" />
                종료
              </button>
            )}
          </div>
        </div>

        {customer.company_description && (
          <p className="mt-4 text-sm text-[var(--text-secondary)]">{customer.company_description}</p>
        )}

        <div className="mt-4 flex flex-wrap gap-4 text-sm text-[var(--text-muted)]">
          {customer.main_product && (
            <span>주요 제품: {customer.main_product}</span>
          )}
          {customer.account_manager_name && (
            <span>담당 PM: {customer.account_manager_name}</span>
          )}
        </div>
      </div>

      {/* 기능 플래그 */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-sm">
        <h2 className="mb-4 text-base font-semibold text-[var(--text-primary)]">기능 설정</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-[var(--text-secondary)]">라이브 프리뷰</p>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              위저드 솔루션 분석 기능 활성화 여부 (Claude API 비용 발생)
            </p>
          </div>
          <button
            type="button"
            disabled={featureLoading}
            onClick={() =>
              handleFeatureToggle(
                "live_preview_enabled",
                Boolean(customer.features?.live_preview_enabled),
              )
            }
            aria-label={
              customer.features?.live_preview_enabled
                ? "라이브 프리뷰 비활성화"
                : "라이브 프리뷰 활성화"
            }
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors focus:outline-none disabled:opacity-50 ${
              customer.features?.live_preview_enabled ? "bg-emerald-500" : "bg-[var(--border-medium)]"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-[var(--bg-surface)] shadow-sm transition-transform ${
                customer.features?.live_preview_enabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
      </div>

      {/* 프로젝트 목록 */}
      <div>
        <h2 className="mb-3 text-base font-medium text-[var(--text-secondary)]">
          프로젝트 ({total}개)
        </h2>

        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-[var(--border-subtle)] py-12 text-[var(--text-muted)]">
            <Layers className="h-8 w-8" />
            <p className="text-sm">등록된 프로젝트가 없습니다</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {projects.map((proj) => (
              <div
                key={proj.id}
                className="flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-5 py-4 shadow-sm transition hover:border-[var(--accent)] hover:shadow-md"
              >
                <button
                  onClick={() =>
                    router.push(`/projects/${proj.id}/ai-team`)
                  }
                  className="flex flex-1 items-center justify-between text-left"
                >
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-[var(--text-primary)]">{proj.name}</span>
                      <span className="rounded-full bg-[var(--bg-base)] px-2 py-0.5 text-xs text-[var(--text-muted)]">
                        {proj.project_type ?? "legacy"}
                      </span>
                    </div>
                    <div className="flex gap-3 text-sm text-[var(--text-muted)]">
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
                        <span className="text-[var(--text-muted)]">소유: {proj.owner_name}</span>
                      )}
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 flex-shrink-0 text-[var(--text-muted)]" />
                </button>

                {/* 프로젝트 삭제 — superadmin 전용 */}
                {isSuperadmin && (
                  <button
                    type="button"
                    onClick={() => setDeleteTarget(proj)}
                    aria-label={`${proj.name} 삭제`}
                    className="flex-shrink-0 rounded-lg p-2 text-[var(--text-muted)] transition-colors hover:bg-red-50 hover:text-red-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 프로젝트 삭제 확인 다이얼로그 (superadmin) */}
      <DeleteProjectDialog
        projectName={deleteTarget?.name ?? ""}
        isOpen={deleteTarget !== null}
        isDeleting={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void handleDeleteProject()}
      />
    </div>
  );
}
