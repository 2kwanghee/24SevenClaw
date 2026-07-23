"use client";

import { useMemo, useState } from "react";
import {
  Loader2,
  Plus,
  Pencil,
  Trash2,
  Search,
  Lock,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import {
  useOpsTables,
  useOpsTableSchema,
  useOpsTableRows,
  useCreateOpsRow,
  useUpdateOpsRow,
  useDeleteOpsRow,
} from "@/hooks/use-ops";
import type { OpsTableColumn } from "@/lib/api-client";
import { ConfirmByTypingDialog } from "@/components/common/confirm-by-typing-dialog";
import { BentoCard } from "@/components/ui/bento";

interface TableCrudProps {
  tableKey: string;
}

type FormValue = string | boolean;
type FormState = Record<string, FormValue>;

const PAGE_SIZE = 25;

function isNumberType(type: string): boolean {
  const t = type.toLowerCase();
  return (
    t.includes("int") ||
    t.includes("float") ||
    t.includes("numeric") ||
    t.includes("decimal") ||
    t.includes("number")
  );
}

function isBoolType(type: string): boolean {
  return type.toLowerCase().includes("bool");
}

function initialForm(columns: OpsTableColumn[]): FormState {
  const form: FormState = {};
  for (const col of columns) {
    form[col.name] = isBoolType(col.type) ? false : "";
  }
  return form;
}

function toFormValue(col: OpsTableColumn, raw: unknown): FormValue {
  if (isBoolType(col.type)) return Boolean(raw);
  if (raw === null || raw === undefined) return "";
  if (typeof raw === "object") return JSON.stringify(raw);
  return String(raw);
}

function coerceOut(col: OpsTableColumn, value: FormValue): unknown {
  if (isBoolType(col.type)) return Boolean(value);
  if (value === "") return null;
  if (isNumberType(col.type)) {
    const n = Number(value);
    return Number.isNaN(n) ? value : n;
  }
  return value;
}

function displayCell(col: OpsTableColumn, raw: unknown): string {
  if (col.sensitive) return "••••••••";
  if (raw === null || raw === undefined) return "-";
  if (typeof raw === "boolean") return raw ? "true" : "false";
  if (typeof raw === "object") return JSON.stringify(raw);
  return String(raw);
}

export function TableCrud({ tableKey }: TableCrudProps) {
  const t = useTranslations("ops.tables");
  const tg = useTranslations("toast.generic");

  const tablesQuery = useOpsTables();
  const schemaQuery = useOpsTableSchema(tableKey);
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const rowsQuery = useOpsTableRows(tableKey, {
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    q: search || undefined,
  });

  const createMut = useCreateOpsRow(tableKey);
  const updateMut = useUpdateOpsRow(tableKey);
  const deleteMut = useDeleteOpsRow(tableKey);

  const [editor, setEditor] = useState<{ pk: string | null; form: FormState } | null>(
    null,
  );
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const schema = schemaQuery.data;
  const columns = schema?.columns ?? [];
  const pkCol = schema?.pk ?? "id";

  const tableInfo = useMemo(
    () => tablesQuery.data?.find((tb) => tb.key === tableKey),
    [tablesQuery.data, tableKey],
  );
  const allowedOps = tableInfo?.ops ?? [];
  const canCreate = allowedOps.includes("create");
  const canUpdate = allowedOps.includes("update");
  const canDelete = allowedOps.includes("delete");

  function openCreate() {
    if (!schema) return;
    setEditor({ pk: null, form: initialForm(columns) });
  }

  function openEdit(row: Record<string, unknown>) {
    if (!schema) return;
    const form: FormState = {};
    for (const col of columns) {
      // sensitive 컬럼은 서버가 마스킹 값(••••)만 주므로 프리필하지 않는다(write-only).
      // 빈 값으로 시작 → 운영자가 실제 입력한 경우에만 저장(handleSave에서 미입력 시 미전송).
      form[col.name] = col.sensitive
        ? isBoolType(col.type)
          ? false
          : ""
        : toFormValue(col, row[col.name]);
    }
    setEditor({ pk: String(row[pkCol]), form });
  }

  function setField(name: string, value: FormValue) {
    setEditor((prev) =>
      prev ? { ...prev, form: { ...prev.form, [name]: value } } : prev,
    );
  }

  async function handleSave() {
    if (!editor || !schema) return;
    const isCreate = editor.pk === null;
    // create → creatable 컬럼만, update → editable 컬럼만 payload에 포함.
    // (자동 컬럼 id/created_at 등 non-creatable 제외 → create mass-assignment/400 회피)
    const values: Record<string, unknown> = {};
    for (const col of columns) {
      const allowed = isCreate ? col.creatable : col.editable;
      if (!allowed) continue;
      const raw = editor.form[col.name] ?? "";
      // sensitive write-only: update 시 미입력이면 기존 값 유지(미전송) — 마스크 리터럴 저장 방지.
      if (col.sensitive && !isCreate && raw === "") continue;
      values[col.name] = coerceOut(col, raw);
    }
    try {
      if (editor.pk === null) {
        await createMut.mutateAsync(values);
        toast.success(t("createSuccess"));
      } else {
        await updateMut.mutateAsync({ pk: editor.pk, values });
        toast.success(t("updateSuccess"));
      }
      setEditor(null);
    } catch {
      toast.error(tg("saveFail"));
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    try {
      await deleteMut.mutateAsync(deleteTarget);
      toast.success(t("deleteSuccess"));
    } catch {
      toast.error(tg("deleteFail"));
    } finally {
      setDeleteTarget(null);
    }
  }

  const total = rowsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const isSaving = createMut.isPending || updateMut.isPending;

  if (schemaQuery.isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" />
      </div>
    );
  }

  if (schemaQuery.isError || !schema) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 py-6 text-center text-sm text-red-700">
        {t("schemaError")}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 검색 + 추가 */}
      <div className="flex items-center justify-between gap-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPage(0);
            setSearch(q);
          }}
          className="flex items-center gap-2"
        >
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("searchPlaceholder")}
              className="w-64 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-1.5 pl-8 pr-3 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            />
          </div>
        </form>

        {canCreate && (
          <button
            type="button"
            onClick={openCreate}
            className="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-[var(--accent-fg)] hover:opacity-90"
          >
            <Plus className="h-3.5 w-3.5" />
            {t("addRow")}
          </button>
        )}
      </div>

      {/* 행 테이블 */}
      {rowsQuery.isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" />
        </div>
      ) : rowsQuery.isError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 py-6 text-center text-sm text-red-700">
          {t("rowsError")}
        </div>
      ) : (rowsQuery.data?.items ?? []).length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border-subtle)] py-8 text-center text-sm text-[var(--text-muted)]">
          {t("noRows")}
        </div>
      ) : (
        <BentoCard className="block overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                {columns.map((col) => (
                  <th
                    key={col.name}
                    className="whitespace-nowrap px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]"
                  >
                    <span className="flex items-center gap-1">
                      {col.name}
                      {col.sensitive && <Lock className="h-3 w-3" />}
                    </span>
                  </th>
                ))}
                {(canUpdate || canDelete) && <th className="px-4 py-2.5" />}
              </tr>
            </thead>
            <tbody>
              {(rowsQuery.data?.items ?? []).map((row, idx) => {
                const pkValue = String(row[pkCol] ?? idx);
                return (
                  <tr
                    key={pkValue}
                    className="border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-hover)]"
                  >
                    {columns.map((col) => (
                      <td
                        key={col.name}
                        className="max-w-[280px] truncate px-4 py-3 text-xs text-[var(--text-secondary)]"
                        title={col.sensitive ? undefined : displayCell(col, row[col.name])}
                      >
                        {displayCell(col, row[col.name])}
                      </td>
                    ))}
                    {(canUpdate || canDelete) && (
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-1">
                          {canUpdate && (
                            <button
                              type="button"
                              onClick={() => openEdit(row)}
                              aria-label={t("edit")}
                              className="rounded-md p-1 text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                          )}
                          {canDelete && (
                            <button
                              type="button"
                              onClick={() => setDeleteTarget(pkValue)}
                              aria-label={t("delete")}
                              className="rounded-md p-1 text-[var(--text-muted)] hover:bg-red-50 hover:text-red-600"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </BentoCard>
      )}

      {/* 페이지네이션 */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
          <span>{t("pageInfo", { page: page + 1, total: totalPages })}</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-lg border border-[var(--border-subtle)] px-3 py-1 hover:bg-[var(--bg-hover)] disabled:opacity-40"
            >
              {t("prev")}
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded-lg border border-[var(--border-subtle)] px-3 py-1 hover:bg-[var(--bg-hover)] disabled:opacity-40"
            >
              {t("next")}
            </button>
          </div>
        </div>
      )}

      {/* 편집/생성 폼 다이얼로그 */}
      {editor && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          role="dialog"
          aria-modal="true"
          aria-label={editor.pk === null ? t("addRow") : t("editRow")}
        >
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setEditor(null)}
            onKeyDown={(e) => e.key === "Escape" && setEditor(null)}
            role="button"
            tabIndex={0}
            aria-label={t("cancel")}
          />
          <div className="relative mx-4 max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-2xl shadow-black/10">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-semibold text-[var(--text-primary)]">
                {editor.pk === null ? t("addRow") : t("editRow")}
              </h3>
              <button
                type="button"
                onClick={() => setEditor(null)}
                aria-label={t("cancel")}
                className="rounded-lg p-1 text-[var(--text-muted)] hover:bg-[var(--bg-hover)]"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              {columns.map((col) => {
                const isCreate = editor.pk === null;
                // create 폼은 creatable, update 폼은 editable 기준으로 비활성.
                const disabled = isCreate ? !col.creatable : !col.editable;
                // sensitive 편집(update)은 write-only: 미입력 시 기존 값 유지 안내.
                const sensitiveKeep = col.sensitive && !isCreate && !disabled;
                const value = editor.form[col.name];
                const fieldId = `field-${col.name}`;
                return (
                  <div key={col.name}>
                    <label
                      htmlFor={fieldId}
                      className="mb-1 flex items-center gap-1.5 text-xs font-medium text-[var(--text-muted)]"
                    >
                      {col.name}
                      {col.required && <span className="text-red-500">*</span>}
                      {disabled && <Lock className="h-3 w-3" />}
                      <span className="text-[10px] font-normal text-[var(--text-muted)]">
                        ({col.type})
                      </span>
                    </label>

                    {isBoolType(col.type) ? (
                      <label className="flex items-center gap-2">
                        <input
                          id={fieldId}
                          type="checkbox"
                          checked={Boolean(value)}
                          disabled={disabled}
                          onChange={(e) => setField(col.name, e.target.checked)}
                          className="h-4 w-4 rounded border-[var(--border-medium)] disabled:opacity-50"
                        />
                        <span className="text-sm text-[var(--text-secondary)]">
                          {String(Boolean(value))}
                        </span>
                      </label>
                    ) : col.enum && col.enum.length > 0 ? (
                      <select
                        id={fieldId}
                        value={String(value ?? "")}
                        disabled={disabled}
                        onChange={(e) => setField(col.name, e.target.value)}
                        className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] disabled:opacity-50"
                      >
                        <option value="">—</option>
                        {col.enum.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        id={fieldId}
                        type={
                          col.sensitive
                            ? "password"
                            : isNumberType(col.type)
                              ? "number"
                              : "text"
                        }
                        value={String(value ?? "")}
                        disabled={disabled}
                        maxLength={col.max_length ?? undefined}
                        onChange={(e) => setField(col.name, e.target.value)}
                        placeholder={
                          disabled
                            ? t("immutable")
                            : sensitiveKeep
                              ? t("sensitiveKeepHint")
                              : undefined
                        }
                        className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] disabled:opacity-50"
                      />
                    )}
                  </div>
                );
              })}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditor(null)}
                className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
              >
                {t("cancel")}
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                {t("save")}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmByTypingDialog
        open={deleteTarget !== null}
        title={t("deleteTitle")}
        description={t("deleteDescription", { pk: deleteTarget ?? "" })}
        confirmPhrase={deleteTarget ?? ""}
        isPending={deleteMut.isPending}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
