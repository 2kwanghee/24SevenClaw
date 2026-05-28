"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  FileText,
  Lock,
  Unlock,
  Plus,
  RefreshCw,
  Pencil,
  X,
  Loader2,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { RoleGuard } from "@/components/common/role-guard";
import { OverrideEditor } from "@/components/contracts/override-editor";
import { TYPE_COLORS, TYPE_LABELS } from "@/components/contracts/contract-viewer";
import {
  useProjectOverrides,
  useContractsList,
  useApplyContractToProject,
  useUpdateOverride,
  useSyncContracts,
  useContract,
} from "@/hooks/use-contracts";
import type {
  CustomerContractOverrideResponse,
} from "@/lib/api-client";

/* -- 오버라이드 카드 -- */

function OverrideCard({
  override,
  projectId,
}: {
  override: CustomerContractOverrideResponse;
  projectId: string;
}) {
  const [editing, setEditing] = useState(false);
  const updateOverride = useUpdateOverride(projectId);
  const tT = useTranslations("toast.contracts");

  const { data: parentContract } = useContract(override.central_contract_id);

  const typeColor = parentContract
    ? TYPE_COLORS[parentContract.contract_type] ?? "bg-zinc-100 text-zinc-600 border-zinc-200"
    : "bg-zinc-100 text-zinc-600 border-zinc-200";
  const typeLabel = parentContract
    ? TYPE_LABELS[parentContract.contract_type] ?? parentContract.contract_type
    : "로딩 중...";

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-lg border px-2 py-0.5 text-xs font-medium ${typeColor}`}
          >
            {typeLabel}
          </span>
          {parentContract && (
            <span className="text-sm font-medium text-[var(--text-primary)]">
              {parentContract.slug}
            </span>
          )}
          {parentContract?.is_locked ? (
            <Lock className="h-3 w-3 text-red-500" />
          ) : (
            <Unlock className="h-3 w-3 text-emerald-600" />
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              override.is_active
                ? "bg-emerald-50 text-emerald-700"
                : "bg-zinc-100 text-zinc-500"
            }`}
          >
            {override.is_active ? "활성" : "비활성"}
          </span>
          <button
            type="button"
            onClick={() => setEditing(!editing)}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            aria-label={editing ? "편집 취소" : "오버라이드 편집"}
          >
            {editing ? <X className="h-3.5 w-3.5" /> : <Pencil className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {editing ? (
        <OverrideEditor
          initialContent={override.override_content}
          allowedFields={parentContract?.allowed_overrides ?? []}
          isLocked={parentContract?.is_locked ?? false}
          isPending={updateOverride.isPending}
          onSave={(content) => {
            updateOverride.mutate(
              { overrideId: override.id, data: { override_content: content } },
              {
                onSuccess: () => {
                  toast.success(tT("overrideUpdateSuccess"));
                  setEditing(false);
                },
                onError: (err) => {
                  toast.error(err.message || tT("overrideUpdateFail"));
                },
              },
            );
          }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <pre className="max-h-40 overflow-auto rounded-lg border border-[var(--border-subtle)] bg-zinc-50 p-3 text-xs leading-relaxed text-zinc-600">
          {JSON.stringify(override.override_content, null, 2)}
        </pre>
      )}

      <div className="mt-2 text-[10px] text-[var(--text-muted)]">
        수정: {new Date(override.updated_at).toLocaleString("ko-KR")}
      </div>
    </div>
  );
}

/* -- 계약 적용 다이얼로그 -- */

function ApplyContractDialog({
  isOpen,
  onClose,
  projectId,
}: {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
}) {
  const { data } = useContractsList({ limit: 100 });
  const applyContract = useApplyContractToProject(projectId);
  const [selectedId, setSelectedId] = useState<string>("");
  const tT = useTranslations("toast.contracts");

  if (!isOpen) return null;

  const handleApply = () => {
    if (!selectedId) return;
    applyContract.mutate(
      { central_contract_id: selectedId, override_content: {} },
      {
        onSuccess: () => {
          toast.success(tT("applySuccess"));
          onClose();
        },
        onError: (err) => {
          toast.error(err.message || tT("applyFail"));
        },
      },
    );
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-[var(--text-primary)]">계약 적용</h3>
            <button
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <p className="mb-4 text-sm text-[var(--text-muted)]">
            프로젝트에 적용할 중앙 계약을 선택하세요.
          </p>

          {data?.items && data.items.length > 0 ? (
            <div className="max-h-60 space-y-1 overflow-y-auto">
              {data.items.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelectedId(c.id)}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left transition-colors ${
                    selectedId === c.id
                      ? "bg-zinc-900 text-white"
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                  }`}
                >
                  <div>
                    <p className="text-sm font-medium">{c.slug}</p>
                    <p className={`text-xs ${selectedId === c.id ? "text-zinc-400" : "text-[var(--text-muted)]"}`}>
                      {TYPE_LABELS[c.contract_type] ?? c.contract_type} · v{c.version}
                    </p>
                  </div>
                  {c.is_locked ? (
                    <Lock className="h-3.5 w-3.5 text-red-500" />
                  ) : (
                    <Unlock className="h-3.5 w-3.5 text-emerald-600" />
                  )}
                </button>
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-[var(--text-muted)]">
              적용 가능한 계약이 없습니다
            </p>
          )}

          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
            >
              취소
            </button>
            <button
              type="button"
              onClick={handleApply}
              disabled={!selectedId || applyContract.isPending}
              className="flex items-center gap-1.5 rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              {applyContract.isPending ? "적용 중..." : "적용"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/* -- 메인 콘텐츠 -- */

function ProjectContractsContent() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data, isLoading, error } = useProjectOverrides(projectId);
  const syncContracts = useSyncContracts(projectId);
  const [applyOpen, setApplyOpen] = useState(false);
  const tT = useTranslations("toast.contracts");

  const handleSync = () => {
    syncContracts.mutate(undefined, {
      onSuccess: (result) => {
        toast.success(tT("syncSuccess", { count: result.synced_count }));
      },
      onError: (err) => {
        toast.error(err.message || tT("syncFail"));
      },
    });
  };

  return (
    <div>
      {/* 브레드크럼 */}
      <div className="mb-6">
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          프로젝트 상세
        </Link>
      </div>

      {/* 헤더 */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-100">
            <FileText className="h-5 w-5 text-zinc-700" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">프로젝트 계약</h1>
            <p className="mt-0.5 text-sm text-[var(--text-muted)]">
              이 프로젝트에 적용된 계약과 오버라이드를 관리합니다
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSync}
            disabled={syncContracts.isPending}
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] disabled:opacity-50"
          >
            {syncContracts.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            동기화
          </button>
          <button
            type="button"
            onClick={() => setApplyOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white transition-all hover:bg-zinc-800"
          >
            <Plus className="h-4 w-4" />
            계약 적용
          </button>
        </div>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-xl bg-zinc-100"
            />
          ))}
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          프로젝트 계약을 불러오지 못했습니다.
        </div>
      )}

      {/* 오버라이드 목록 */}
      {data?.items && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((override) => (
            <OverrideCard
              key={override.id}
              override={override}
              projectId={projectId}
            />
          ))}
          <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
            총 {data.total}개
          </p>
        </div>
      )}

      {/* 빈 상태 */}
      {data?.items && data.items.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <FileText className="h-12 w-12 text-zinc-400" />
          <p className="text-sm text-[var(--text-muted)]">
            적용된 계약이 없습니다
          </p>
          <button
            type="button"
            onClick={() => setApplyOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-zinc-800"
          >
            <Plus className="h-3.5 w-3.5" />
            첫 계약 적용
          </button>
        </div>
      )}

      {/* 적용 다이얼로그 */}
      <ApplyContractDialog
        isOpen={applyOpen}
        onClose={() => setApplyOpen(false)}
        projectId={projectId}
      />
    </div>
  );
}

export default function ProjectContractsPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <Suspense
        fallback={
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-32 animate-pulse rounded-xl bg-zinc-100"
              />
            ))}
          </div>
        }
      >
        <ProjectContractsContent />
      </Suspense>
    </RoleGuard>
  );
}
