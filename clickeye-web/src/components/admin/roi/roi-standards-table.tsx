"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, X, Check, Loader2 } from "lucide-react";

import {
  useRoiStandards,
  useCreateRoiStandard,
  useUpdateRoiStandard,
  useDeleteRoiStandard,
} from "@/hooks/use-roi-standards";
import {
  type RoiStandardResponse,
  type RoiStandardCreateRequest,
} from "@/lib/api-client";

type Category = "role_rate" | "solution_effort" | "complexity_multiplier";

interface Props {
  category: Category;
}

const CATEGORY_META: Record<Category, { unit: string; valueType: "numeric" | "json" }> = {
  role_rate: { unit: "KRW/day", valueType: "numeric" },
  solution_effort: { unit: "days", valueType: "json" },
  complexity_multiplier: { unit: "multiplier", valueType: "numeric" },
};

const ROLE_KEYS = ["pm", "be", "fe", "qa", "designer"];

function formatValue(item: RoiStandardResponse): string {
  if (item.value_numeric !== null) {
    if (item.unit === "KRW/day") {
      return `${Number(item.value_numeric).toLocaleString("ko-KR")}원`;
    }
    return String(item.value_numeric);
  }
  if (item.value_json) {
    return Object.entries(item.value_json)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => `${k}:${v}일`)
      .join(" / ");
  }
  return "-";
}

interface EditorState {
  id: string | null;
  key: string;
  label: string;
  value_numeric: string;
  value_json: Record<string, string>;
  is_active: boolean;
}

const emptyEditor = (category: Category): EditorState => ({
  id: null,
  key: "",
  label: "",
  value_numeric: "",
  value_json: Object.fromEntries(ROLE_KEYS.map((k) => [k, "0"])),
  is_active: true,
});

export function RoiStandardsTable({ category }: Props) {
  const { data, isLoading } = useRoiStandards(category);
  const createMut = useCreateRoiStandard();
  const updateMut = useUpdateRoiStandard();
  const deleteMut = useDeleteRoiStandard();

  const [editor, setEditor] = useState<EditorState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const meta = CATEGORY_META[category];

  function openCreate() {
    setEditor(emptyEditor(category));
  }

  function openEdit(item: RoiStandardResponse) {
    setEditor({
      id: item.id,
      key: item.key,
      label: item.label,
      value_numeric: item.value_numeric !== null ? String(item.value_numeric) : "",
      value_json: item.value_json
        ? Object.fromEntries(ROLE_KEYS.map((k) => [k, String(item.value_json?.[k] ?? 0)]))
        : Object.fromEntries(ROLE_KEYS.map((k) => [k, "0"])),
      is_active: item.is_active,
    });
  }

  function closeEditor() {
    setEditor(null);
  }

  async function handleSave() {
    if (!editor) return;

    const payload: RoiStandardCreateRequest = {
      category,
      key: editor.key,
      label: editor.label,
      unit: meta.unit,
      is_active: editor.is_active,
    };

    if (meta.valueType === "numeric") {
      payload.value_numeric = parseFloat(editor.value_numeric) || 0;
    } else {
      payload.value_json = Object.fromEntries(
        ROLE_KEYS.map((k) => [k, parseFloat(editor.value_json[k] ?? "0") || 0])
      );
    }

    if (editor.id) {
      await updateMut.mutateAsync({ id: editor.id, data: payload });
    } else {
      await createMut.mutateAsync(payload);
    }
    closeEditor();
  }

  const isPending = createMut.isPending || updateMut.isPending;

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800"
        >
          <Plus className="h-3.5 w-3.5" />
          항목 추가
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">키</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">레이블</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">값</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">상태</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-hover)]"
                >
                  <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)]">{item.key}</td>
                  <td className="px-4 py-3 text-[var(--text-primary)]">{item.label}</td>
                  <td className="px-4 py-3 text-[var(--text-secondary)]">{formatValue(item)}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-md px-2 py-0.5 text-xs font-medium ${
                        item.is_active
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-zinc-100 text-zinc-400"
                      }`}
                    >
                      {item.is_active ? "활성" : "비활성"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => openEdit(item)}
                        className="rounded-md p-1.5 text-[var(--text-muted)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      {deleteTarget === item.id ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              deleteMut.mutate(item.id);
                              setDeleteTarget(null);
                            }}
                            className="rounded-md p-1.5 text-red-600 hover:bg-red-50"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteTarget(null)}
                            className="rounded-md p-1.5 text-[var(--text-muted)] hover:bg-[var(--bg-surface)]"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteTarget(item.id)}
                          className="rounded-md p-1.5 text-[var(--text-muted)] hover:bg-red-50 hover:text-red-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {(data?.items ?? []).length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-[var(--text-muted)]">
                    항목이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {editor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-lg">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-base font-semibold text-[var(--text-primary)]">
                {editor.id ? "항목 수정" : "항목 추가"}
              </h3>
              <button onClick={closeEditor} className="rounded-lg p-1.5 text-[var(--text-muted)] hover:bg-[var(--bg-hover)]">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--text-muted)]">키 (key)</label>
                <input
                  value={editor.key}
                  onChange={(e) => setEditor((p) => p && { ...p, key: e.target.value })}
                  disabled={!!editor.id}
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 font-mono text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-zinc-300 disabled:opacity-50"
                  placeholder="예: pm, saas, high"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--text-muted)]">레이블</label>
                <input
                  value={editor.label}
                  onChange={(e) => setEditor((p) => p && { ...p, label: e.target.value })}
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-zinc-300"
                  placeholder="예: 프로젝트 매니저"
                />
              </div>

              {meta.valueType === "numeric" ? (
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                    값 ({meta.unit})
                  </label>
                  <input
                    type="number"
                    value={editor.value_numeric}
                    onChange={(e) => setEditor((p) => p && { ...p, value_numeric: e.target.value })}
                    className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-zinc-300"
                    placeholder="예: 900000"
                  />
                </div>
              ) : (
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--text-muted)]">
                    직군별 공수 (일)
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {ROLE_KEYS.map((k) => (
                      <div key={k}>
                        <label className="mb-0.5 block text-[10px] text-[var(--text-muted)]">{k}</label>
                        <input
                          type="number"
                          value={editor.value_json[k] ?? "0"}
                          onChange={(e) =>
                            setEditor((p) =>
                              p ? { ...p, value_json: { ...p.value_json, [k]: e.target.value } } : null
                            )
                          }
                          className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-1 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-zinc-300"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editor.is_active}
                  onChange={(e) => setEditor((p) => p && { ...p, is_active: e.target.checked })}
                  className="h-4 w-4 rounded border-zinc-300"
                />
                <span className="text-sm text-[var(--text-secondary)]">활성</span>
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={closeEditor}
                className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
              >
                취소
              </button>
              <button
                onClick={handleSave}
                disabled={isPending || !editor.key || !editor.label}
                className="flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                저장
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
