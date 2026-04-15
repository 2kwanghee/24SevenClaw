"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Save,
  X,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

import { RoleGuard } from "@/components/common/role-guard";
import { ContractViewer } from "@/components/contracts/contract-viewer";
import { ContractAuditTable } from "@/components/contracts/contract-audit-table";
import {
  useContract,
  useUpdateContract,
  useDeleteContract,
} from "@/hooks/use-contracts";
import type { CentralContractUpdateRequest } from "@/lib/api-client";
import { TYPE_LABELS } from "@/components/contracts/contract-viewer";

const TYPE_OPTIONS = ["settings", "skill", "agent", "pipeline"];

function EditForm({
  contract,
  onCancel,
}: {
  contract: {
    id: string;
    slug: string;
    contract_type: string;
    source: string;
    version: string;
    content: Record<string, unknown>;
    description: string | null;
    is_locked: boolean;
    allowed_overrides: string[];
  };
  onCancel: () => void;
}) {
  const updateContract = useUpdateContract(contract.id);
  const [formData, setFormData] = useState<CentralContractUpdateRequest>({
    contract_type: contract.contract_type,
    source: contract.source,
    version: contract.version,
    description: contract.description ?? "",
    is_locked: contract.is_locked,
    allowed_overrides: contract.allowed_overrides,
  });
  const [contentText, setContentText] = useState(
    JSON.stringify(contract.content, null, 2),
  );
  const [overridesText, setOverridesText] = useState(
    contract.allowed_overrides.join(", "),
  );
  const [formError, setFormError] = useState<string | null>(null);

  const handleSave = () => {
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
    updateContract.mutate(
      { ...formData, content, allowed_overrides },
      {
        onSuccess: () => {
          toast.success("계약이 수정되었습니다");
          onCancel();
        },
        onError: (err) => {
          toast.error(err.message || "계약 수정에 실패했습니다");
        },
      },
    );
  };

  return (
    <div className="space-y-4">
      {/* 타입 + 소스 + 버전 */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label htmlFor="edit-type" className="mb-1 block text-xs font-medium text-slate-400">
            타입
          </label>
          <select
            id="edit-type"
            value={formData.contract_type ?? ""}
            onChange={(e) => setFormData({ ...formData, contract_type: e.target.value })}
            className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200 focus:border-violet-500/30 focus:outline-none"
          >
            {TYPE_OPTIONS.map((type) => (
              <option key={type} value={type}>
                {TYPE_LABELS[type] ?? type}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="edit-source" className="mb-1 block text-xs font-medium text-slate-400">
            소스
          </label>
          <input
            id="edit-source"
            type="text"
            value={formData.source ?? ""}
            onChange={(e) => setFormData({ ...formData, source: e.target.value })}
            className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200 focus:border-violet-500/30 focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="edit-version" className="mb-1 block text-xs font-medium text-slate-400">
            버전
          </label>
          <input
            id="edit-version"
            type="text"
            value={formData.version ?? ""}
            onChange={(e) => setFormData({ ...formData, version: e.target.value })}
            className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200 focus:border-violet-500/30 focus:outline-none"
          />
        </div>
      </div>

      {/* 설명 + 잠금 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="edit-desc" className="mb-1 block text-xs font-medium text-slate-400">
            설명
          </label>
          <input
            id="edit-desc"
            type="text"
            value={formData.description ?? ""}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200 focus:border-violet-500/30 focus:outline-none"
          />
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 py-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={formData.is_locked ?? false}
              onChange={(e) => setFormData({ ...formData, is_locked: e.target.checked })}
              className="h-4 w-4 rounded border-white/10 bg-white/[0.03] text-violet-500 focus:ring-violet-500/30"
            />
            잠금 상태
          </label>
        </div>
      </div>

      {/* 허용 오버라이드 */}
      <div>
        <label htmlFor="edit-overrides" className="mb-1 block text-xs font-medium text-slate-400">
          허용 오버라이드 필드 (쉼표 구분)
        </label>
        <input
          id="edit-overrides"
          type="text"
          value={overridesText}
          onChange={(e) => setOverridesText(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200 focus:border-violet-500/30 focus:outline-none"
        />
      </div>

      {/* JSON 콘텐츠 */}
      <div>
        <label htmlFor="edit-content" className="mb-1 block text-xs font-medium text-slate-400">
          콘텐츠 (JSON)
        </label>
        <textarea
          id="edit-content"
          value={contentText}
          onChange={(e) => setContentText(e.target.value)}
          rows={12}
          spellCheck={false}
          className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 font-mono text-xs leading-relaxed text-slate-300 focus:border-violet-500/30 focus:outline-none"
        />
      </div>

      {/* 에러 */}
      {formError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 text-red-400" />
          <p className="text-xs text-red-300">{formError}</p>
        </div>
      )}

      {/* 액션 */}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-white/[0.05]"
        >
          <X className="h-3.5 w-3.5" />
          취소
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={updateContract.isPending}
          className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Save className="h-3.5 w-3.5" />
          {updateContract.isPending ? "저장 중..." : "저장"}
        </button>
      </div>
    </div>
  );
}

function ContractDetailContent() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: contract, isLoading, error } = useContract(id);
  const deleteContract = useDeleteContract();
  const [isEditing, setIsEditing] = useState(false);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        <p className="mt-4 text-sm text-slate-500">불러오는 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center">
        <p className="text-sm text-red-300">
          계약을 불러오지 못했습니다: {error.message}
        </p>
      </div>
    );
  }

  if (!contract) return null;

  const handleDelete = () => {
    if (!confirm("이 계약을 삭제하시겠습니까?")) return;
    deleteContract.mutate(contract.id, {
      onSuccess: () => {
        toast.success("계약이 삭제되었습니다");
        router.push("/admin/contracts");
      },
      onError: (err) => {
        toast.error(err.message || "계약 삭제에 실패했습니다");
      },
    });
  };

  return (
    <div>
      {/* 브레드크럼 */}
      <div className="mb-6">
        <Link
          href="/admin/contracts"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-slate-300"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          계약 목록
        </Link>
      </div>

      {/* 헤더 */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{contract.slug}</h1>
          <p className="mt-1 text-sm text-slate-500">
            ID: {contract.id}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setIsEditing(!isEditing)}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
          >
            <Pencil className="h-3.5 w-3.5" />
            {isEditing ? "보기 모드" : "수정"}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleteContract.isPending}
            className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-2 text-sm font-medium text-red-400 transition-all hover:bg-red-500/10 disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            삭제
          </button>
        </div>
      </div>

      {/* 콘텐츠 영역 */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
        {isEditing ? (
          <EditForm contract={contract} onCancel={() => setIsEditing(false)} />
        ) : (
          <ContractViewer contract={contract} />
        )}
      </div>

      {/* 감사 로그 */}
      <div className="mt-8 rounded-2xl border border-white/5 bg-white/[0.02] p-6">
        <ContractAuditTable contractId={contract.id} />
      </div>
    </div>
  );
}

export default function AdminContractDetailPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <Suspense
        fallback={
          <div className="flex flex-col items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
            <p className="mt-4 text-sm text-slate-500">불러오는 중...</p>
          </div>
        }
      >
        <ContractDetailContent />
      </Suspense>
    </RoleGuard>
  );
}
