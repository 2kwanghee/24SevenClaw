"use client";

import { useState } from "react";
import { Loader2, Lock, Pencil, Trash2, Check, X, PlayCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import {
  useOpsEnv,
  usePutOpsEnv,
  useDeleteOpsEnv,
  useRenderOpsEnv,
} from "@/hooks/use-ops";
import type { OpsEnvVar, OpsEnvRenderResponse } from "@/lib/api-client";
import { ConfirmByTypingDialog } from "@/components/common/confirm-by-typing-dialog";
import { RenderCommandDialog } from "@/components/admin/ops/render-command-dialog";

export function EnvPanel() {
  const t = useTranslations("ops.env");
  const tg = useTranslations("toast.generic");
  const { data, isLoading, isError } = useOpsEnv();
  const putMut = usePutOpsEnv();
  const deleteMut = useDeleteOpsEnv();
  const renderMut = useRenderOpsEnv();

  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [renderResult, setRenderResult] = useState<OpsEnvRenderResponse | null>(
    null,
  );

  const items = data ?? [];
  const pendingCount = items.filter((e) => e.pending).length;

  function startEdit(item: OpsEnvVar) {
    setEditingKey(item.key);
    setEditValue("");
  }

  function cancelEdit() {
    setEditingKey(null);
    setEditValue("");
  }

  async function saveEdit(key: string) {
    try {
      await putMut.mutateAsync({ key, value: editValue });
      toast.success(t("saveSuccess"));
      cancelEdit();
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

  async function handleRender() {
    try {
      const res = await renderMut.mutateAsync(true);
      setRenderResult(res);
    } catch {
      toast.error(t("render.error"));
    }
  }

  function displayValue(item: OpsEnvVar): string {
    if (item.is_secret) return item.masked_value ?? "••••••••";
    if (item.masked_value) return item.masked_value;
    return item.has_value ? t("valueSet") : t("valueUnset");
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-[var(--text-muted)]">
          {pendingCount > 0
            ? t("pendingSummary", { count: pendingCount })
            : t("noPending")}
        </p>
        <button
          type="button"
          onClick={handleRender}
          disabled={renderMut.isPending}
          className="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-[var(--accent-fg)] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {renderMut.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <PlayCircle className="h-3.5 w-3.5" />
          )}
          {t("render.button")}
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" />
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 py-6 text-center text-sm text-red-700">
          {t("error")}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--border-subtle)] py-8 text-center text-sm text-[var(--text-muted)]">
          {t("empty")}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[var(--border-subtle)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.key")}
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.value")}
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.status")}
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.updated")}
                </th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isEditing = editingKey === item.key;
                return (
                  <tr
                    key={item.key}
                    className={`border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-hover)] ${
                      item.pending ? "bg-amber-50/60" : ""
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-xs font-medium text-[var(--text-primary)]">
                      <span className="flex items-center gap-1.5">
                        {item.key}
                        {item.is_secret && (
                          <Lock
                            className="h-3 w-3 text-[var(--text-muted)]"
                            aria-label={t("secret")}
                          />
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)]">
                      {isEditing ? (
                        <input
                          type={item.is_secret ? "password" : "text"}
                          value={editValue}
                          autoFocus
                          onChange={(e) => setEditValue(e.target.value)}
                          placeholder={t("newValuePlaceholder")}
                          className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-1 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                        />
                      ) : (
                        displayValue(item)
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {item.pending ? (
                        <span className="inline-flex items-center rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                          {t("pendingBadge")}
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-md border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-muted)]">
                          {t("appliedBadge")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
                      {item.updated_at ? (
                        <span>
                          {item.updated_at}
                          {item.updated_by ? ` · ${item.updated_by}` : ""}
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {!item.editable ? (
                        <span className="flex items-center justify-end gap-1 text-[11px] text-[var(--text-muted)]">
                          <Lock className="h-3 w-3" />
                          {t("locked")}
                        </span>
                      ) : isEditing ? (
                        <div className="flex justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => saveEdit(item.key)}
                            disabled={putMut.isPending}
                            aria-label={t("save")}
                            className="rounded-md p-1 text-green-600 hover:bg-green-50 disabled:opacity-50"
                          >
                            {putMut.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Check className="h-4 w-4" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={cancelEdit}
                            aria-label={t("cancel")}
                            className="rounded-md p-1 text-[var(--text-muted)] hover:bg-[var(--bg-hover)]"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => startEdit(item)}
                            aria-label={t("edit")}
                            className="rounded-md p-1 text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(item.key)}
                            aria-label={t("delete")}
                            className="rounded-md p-1 text-[var(--text-muted)] hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmByTypingDialog
        open={deleteTarget !== null}
        title={t("deleteTitle")}
        description={t("deleteDescription", { key: deleteTarget ?? "" })}
        confirmPhrase={deleteTarget ?? ""}
        isPending={deleteMut.isPending}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      <RenderCommandDialog
        open={renderResult !== null}
        result={renderResult}
        onClose={() => setRenderResult(null)}
      />
    </div>
  );
}
