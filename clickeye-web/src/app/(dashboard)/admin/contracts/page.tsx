"use client";

import { Suspense, useCallback, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Plus,
  ChevronLeft,
  ChevronRight,
  Filter,
  Lock,
  Unlock,
  X,
  AlertCircle,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { RoleGuard } from "@/components/common/role-guard";
import { BentoCard } from "@/components/ui/bento";
import { useContractsList, useCreateContract } from "@/hooks/use-contracts";
import { TYPE_COLORS, TYPE_LABELS } from "@/components/contracts/contract-viewer";
import type { CentralContractResponse, CentralContractCreateRequest } from "@/lib/api-client";

const PAGE_SIZE = 20;

const TYPE_OPTIONS = ["settings", "skill", "agent", "pipeline"];

function ContractRow({ contract }: { contract: CentralContractResponse }) {
  const typeColor =
    TYPE_COLORS[contract.contract_type] ?? "bg-[var(--bg-hover)] text-[var(--text-secondary)] border-[var(--border-subtle)]";
  const typeLabel = TYPE_LABELS[contract.contract_type] ?? contract.contract_type;

  return (
    <tr className="border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-hover)]">
      <td className="px-4 py-3">
        <Link
          href={`/admin/contracts/${contract.id}`}
          className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        >
          {contract.slug}
        </Link>
        {contract.description && (
          <p className="mt-0.5 line-clamp-1 text-xs text-[var(--text-muted)]">
            {contract.description}
          </p>
        )}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-xs font-medium ${typeColor}`}
        >
          {typeLabel}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">{contract.version}</td>
      <td className="px-4 py-3">
        {contract.is_locked ? (
          <span className="inline-flex items-center gap-1 text-xs text-red-700">
            <Lock className="h-3 w-3" />
            잠금
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
            <Unlock className="h-3 w-3" />
            편집 가능
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
        {contract.source}
      </td>
      <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
        {new Date(contract.updated_at).toLocaleDateString("ko-KR")}
      </td>
    </tr>
  );
}

function CreateContractDialog({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const createContract = useCreateContract();
  const tT = useTranslations("toast.contracts");
  const [formData, setFormData] = useState<CentralContractCreateRequest>({
    slug: "",
    contract_type: "settings",
    source: "central",
    version: "1.0.0",
    content: {},
    description: "",
    is_locked: true,
    allowed_overrides: [],
  });
  const [contentText, setContentText] = useState("{}");
  const [overridesText, setOverridesText] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!formData.slug.trim()) {
      setFormError("슬러그를 입력하세요");
      return;
    }

    let content: Record<string, unknown>;
    try {
      content = JSON.parse(contentText) as Record<string, unknown>;
    } catch {
      setFormError("콘텐츠 JSON 형식이 올바르지 않습니다");
      return;
    }

    const allowed_overrides = overridesText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    setFormError(null);
    createContract.mutate(
      { ...formData, content, allowed_overrides },
      {
        onSuccess: () => {
          toast.success(tT("createSuccess"));
          onClose();
        },
        onError: (err) => {
          toast.error(err.message || tT("createFail"));
        },
      },
    );
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="w-full max-w-lg rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">새 계약 생성</h2>
            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-4">
            {/* 슬러그 */}
            <div>
              <label htmlFor="slug" className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                슬러그 *
              </label>
              <input
                id="slug"
                type="text"
                value={formData.slug}
                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder="예: default-settings"
              />
            </div>

            {/* 타입 + 소스 */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="contract_type" className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                  타입
                </label>
                <select
                  id="contract_type"
                  value={formData.contract_type}
                  onChange={(e) => setFormData({ ...formData, contract_type: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
                >
                  {TYPE_OPTIONS.map((type) => (
                    <option key={type} value={type}>
                      {TYPE_LABELS[type] ?? type}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="source" className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                  소스
                </label>
                <input
                  id="source"
                  type="text"
                  value={formData.source}
                  onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                  placeholder="central"
                />
              </div>
            </div>

            {/* 버전 + 잠금 */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="version" className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                  버전
                </label>
                <input
                  id="version"
                  type="text"
                  value={formData.version}
                  onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                  placeholder="1.0.0"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 py-2 text-sm text-[var(--text-secondary)]">
                  <input
                    type="checkbox"
                    checked={formData.is_locked}
                    onChange={(e) => setFormData({ ...formData, is_locked: e.target.checked })}
                    className="h-4 w-4 rounded border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--accent)] focus:ring-[var(--accent)]"
                  />
                  잠금 상태
                </label>
              </div>
            </div>

            {/* 설명 */}
            <div>
              <label htmlFor="description" className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                설명
              </label>
              <input
                id="description"
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder="계약 설명"
              />
            </div>

            {/* 허용 오버라이드 */}
            <div>
              <label htmlFor="allowed_overrides" className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                허용 오버라이드 필드 (쉼표 구분)
              </label>
              <input
                id="allowed_overrides"
                type="text"
                value={overridesText}
                onChange={(e) => setOverridesText(e.target.value)}
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder="예: timeout, retry_count"
              />
            </div>

            {/* 콘텐츠 */}
            <div>
              <label htmlFor="content" className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                콘텐츠 (JSON)
              </label>
              <textarea data-gramm="false" data-gramm_editor="false"
                id="content"
                value={contentText}
                onChange={(e) => setContentText(e.target.value)}
                rows={4}
                spellCheck={false}
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 font-mono text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
                placeholder='{ "key": "value" }'
              />
            </div>

            {/* 에러 */}
            {formError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
                <AlertCircle className="h-3.5 w-3.5 shrink-0 text-red-700" />
                <p className="text-xs text-red-700">{formError}</p>
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              취소
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={createContract.isPending}
              className="flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              {createContract.isPending ? "생성 중..." : "생성"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function ContractsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const currentPage = Math.max(1, Number(searchParams.get("page") ?? "1"));
  const typeFilter = searchParams.get("contract_type") ?? "";

  const [filterOpen, setFilterOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

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

  const { data, isLoading, error } = useContractsList({
    contract_type: typeFilter || undefined,
    limit: PAGE_SIZE,
    offset,
  });

  const items = data?.items;
  const hasMore = items && items.length === PAGE_SIZE;

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
            <FileText className="h-5 w-5 text-[var(--text-secondary)]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">계약 관리</h1>
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">
              중앙 계약을 관리하고 프로젝트에 배포합니다
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* 타입 필터 */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setFilterOpen(!filterOpen)}
              className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)]"
            >
              <Filter className="h-4 w-4" />
              {typeFilter ? TYPE_LABELS[typeFilter] ?? typeFilter : "모든 타입"}
            </button>
            {filterOpen && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setFilterOpen(false)}
                />
                <div className="absolute right-0 z-20 mt-1 w-40 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1 shadow-xl">
                  <button
                    type="button"
                    onClick={() => {
                      updateParams({ contract_type: "", page: "" });
                      setFilterOpen(false);
                    }}
                    className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                      !typeFilter
                        ? "bg-[var(--bg-hover)] text-[var(--text-secondary)]"
                        : "text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
                    }`}
                  >
                    모든 타입
                  </button>
                  {TYPE_OPTIONS.map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        updateParams({ contract_type: type, page: "" });
                        setFilterOpen(false);
                      }}
                      className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                        typeFilter === type
                          ? "bg-[var(--bg-hover)] text-[var(--text-secondary)]"
                          : "text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
                      }`}
                    >
                      {TYPE_LABELS[type] ?? type}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* 생성 버튼 */}
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-[var(--accent-fg)] transition-all hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            새 계약
          </button>
        </div>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-xl bg-[var(--bg-surface)]"
            />
          ))}
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          계약 목록을 불러오지 못했습니다.
        </div>
      )}

      {/* 테이블 */}
      {items && items.length > 0 && (
        <BentoCard className="block overflow-x-auto p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  슬러그
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  타입
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  버전
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  잠금
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  소스
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
                  수정일
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <ContractRow key={c.id} contract={c} />
              ))}
            </tbody>
          </table>
        </BentoCard>
      )}

      {/* 빈 상태 */}
      {items && items.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <FileText className="h-12 w-12 text-[var(--text-muted)]" />
          <p className="text-sm text-[var(--text-muted)]">등록된 계약이 없습니다</p>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-all hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" />
            첫 계약 생성
          </button>
        </div>
      )}

      {/* 페이지네이션 */}
      {items && items.length > 0 && (
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => updateParams({ page: String(currentPage - 1) })}
            aria-label="이전 페이지"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-muted)] transition-colors hover:border-[var(--border-medium)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm text-[var(--text-muted)]">{currentPage} 페이지</span>
          <button
            type="button"
            disabled={!hasMore}
            onClick={() => updateParams({ page: String(currentPage + 1) })}
            aria-label="다음 페이지"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-muted)] transition-colors hover:border-[var(--border-medium)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 총 개수 */}
      {data && (
        <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
          총 {data.total}개
        </p>
      )}

      {/* 생성 다이얼로그 */}
      <CreateContractDialog isOpen={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

export default function AdminContractsPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <Suspense
        fallback={
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-14 animate-pulse rounded-xl bg-[var(--bg-surface)]"
              />
            ))}
          </div>
        }
      >
        <ContractsContent />
      </Suspense>
    </RoleGuard>
  );
}
