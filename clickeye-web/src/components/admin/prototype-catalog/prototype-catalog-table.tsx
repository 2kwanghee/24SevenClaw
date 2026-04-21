"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, AlertCircle, ToggleLeft, ToggleRight } from "lucide-react";
import { toast } from "sonner";

import type { PrototypeCatalogEntry } from "@/lib/api-client";
import { useCatalogEntries, useDeleteCatalogEntry } from "@/hooks/use-prototype-catalog-admin";
import { PrototypeCatalogEditorDrawer } from "./prototype-catalog-editor-drawer";

export function PrototypeCatalogTable() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editEntry, setEditEntry] = useState<PrototypeCatalogEntry | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  const { data, isLoading, error } = useCatalogEntries(
    showInactive ? { is_active: undefined } : { is_active: true }
  );
  const deleteMutation = useDeleteCatalogEntry();

  const openCreate = () => { setEditEntry(null); setDrawerOpen(true); };
  const openEdit = (e: PrototypeCatalogEntry) => { setEditEntry(e); setDrawerOpen(true); };

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("삭제되었습니다");
    } catch {
      toast.error("삭제에 실패했습니다");
    }
    setDeleteConfirm(null);
  };

  const items = data?.items ?? [];

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowInactive(v => !v)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-white"
          >
            {showInactive ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
            비활성 포함
          </button>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-500"
        >
          <Plus size={12} />
          새 항목
        </button>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-xs text-slate-500">로딩 중...</div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-400">
          <AlertCircle size={14} />
          불러오기 실패: {error.message}
        </div>
      )}

      {!isLoading && !error && (
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                <th className="px-4 py-3 text-left font-medium text-slate-400">제목</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">Slug</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">대표 태그</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">기술 스택</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">우선순위</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">상태</th>
                <th className="px-4 py-3 text-right font-medium text-slate-400">액션</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-600">
                    카탈로그 항목이 없습니다
                  </td>
                </tr>
              ) : (
                items.map(item => (
                  <tr key={item.id} className="border-b border-white/5 hover:bg-white/3">
                    <td className="px-4 py-3 text-white font-medium max-w-[200px]">
                      <div className="truncate">{item.title}</div>
                      {item.description && (
                        <div className="text-slate-500 text-xs truncate mt-0.5">{item.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-400">{item.slug}</td>
                    <td className="px-4 py-3">
                      {item.primary_tag && (
                        <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-blue-400 text-xs">
                          {item.primary_tag}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-[150px]">
                      <div className="truncate">{item.tech_stack_tags.join(", ")}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-center">{item.priority}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${
                        item.is_active
                          ? "bg-green-500/20 text-green-400"
                          : "bg-slate-500/20 text-slate-500"
                      }`}>
                        {item.is_active ? "활성" : "비활성"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(item)}
                          className="rounded p-1.5 text-slate-500 hover:text-white hover:bg-white/10"
                          title="편집"
                        >
                          <Pencil size={12} />
                        </button>
                        {deleteConfirm === item.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => handleDelete(item.id)}
                              className="rounded px-2 py-1 text-xs bg-red-600 text-white hover:bg-red-500"
                            >
                              삭제
                            </button>
                            <button
                              type="button"
                              onClick={() => setDeleteConfirm(null)}
                              className="rounded px-2 py-1 text-xs text-slate-500 hover:text-white"
                            >
                              취소
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setDeleteConfirm(item.id)}
                            className="rounded p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                            title="삭제"
                          >
                            <Trash2 size={12} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <PrototypeCatalogEditorDrawer
        key={editEntry?.id ?? "new"}
        entry={editEntry}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  );
}
