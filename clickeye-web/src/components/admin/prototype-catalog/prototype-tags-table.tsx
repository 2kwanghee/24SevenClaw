"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

import type { PrototypeTag } from "@/lib/api-client";
import {
  usePrototypeTags,
  useCreatePrototypeTag,
  useUpdatePrototypeTag,
  useDeletePrototypeTag,
} from "@/hooks/use-prototype-catalog-admin";

type TagFormState = {
  slug: string;
  label: string;
  label_ko: string;
  description: string;
  color: string;
  is_active: boolean;
  sort_order: string;
};

function tagToForm(tag: PrototypeTag | null): TagFormState {
  if (!tag) return { slug: "", label: "", label_ko: "", description: "", color: "", is_active: true, sort_order: "0" };
  return {
    slug: tag.slug,
    label: tag.label,
    label_ko: tag.label_ko ?? "",
    description: tag.description ?? "",
    color: tag.color ?? "",
    is_active: tag.is_active,
    sort_order: String(tag.sort_order),
  };
}

const INPUT = "w-full rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-xs text-white placeholder:text-slate-600 focus:border-blue-500 focus:outline-none";

function TagEditorDrawer({ tag, open, onClose }: { tag: PrototypeTag | null; open: boolean; onClose: () => void }) {
  const [form, setForm] = useState<TagFormState>(tagToForm(null));
  const createMutation = useCreatePrototypeTag();
  const updateMutation = useUpdatePrototypeTag();
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  useState(() => { if (open) setForm(tagToForm(tag)); });

  const set = (key: keyof TagFormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => setForm(prev => ({ ...prev, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      slug: form.slug,
      label: form.label,
      label_ko: form.label_ko || null,
      description: form.description || null,
      color: form.color || null,
      is_active: form.is_active,
      sort_order: parseInt(form.sort_order, 10) || 0,
    };
    try {
      if (tag) {
        await updateMutation.mutateAsync({ id: tag.id, data: payload });
        toast.success("태그가 수정되었습니다");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("태그가 생성되었습니다");
      }
      onClose();
    } catch { toast.error("저장에 실패했습니다"); }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} role="button" tabIndex={0} onKeyDown={e => e.key === "Escape" && onClose()} aria-label="닫기" />
      <div className="relative w-full max-w-md h-full overflow-y-auto border-l border-white/10 bg-slate-900">
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
          <h2 className="text-sm font-semibold text-white">{tag ? "태그 편집" : "새 태그"}</h2>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-white">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">
          <div><label className="text-xs text-slate-400 mb-1 block">Slug *</label>
            <input className={INPUT} value={form.slug} onChange={set("slug")} required disabled={!!tag} /></div>
          <div><label className="text-xs text-slate-400 mb-1 block">레이블 (영문) *</label>
            <input className={INPUT} value={form.label} onChange={set("label")} required /></div>
          <div><label className="text-xs text-slate-400 mb-1 block">레이블 (한국어)</label>
            <input className={INPUT} value={form.label_ko} onChange={set("label_ko")} /></div>
          <div><label className="text-xs text-slate-400 mb-1 block">설명</label>
            <input className={INPUT} value={form.description} onChange={set("description")} /></div>
          <div><label className="text-xs text-slate-400 mb-1 block">컬러 코드 (예: #3B82F6)</label>
            <input className={INPUT} value={form.color} onChange={set("color")} /></div>
          <div><label className="text-xs text-slate-400 mb-1 block">정렬 순서</label>
            <input type="number" className={INPUT} value={form.sort_order} onChange={set("sort_order")} /></div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.is_active} onChange={e => setForm(prev => ({ ...prev, is_active: e.target.checked }))} />
            <span className="text-xs text-slate-400">활성</span>
          </label>
          <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
            <button type="button" onClick={onClose} className="rounded-lg border border-white/10 px-4 py-2 text-xs text-slate-400 hover:text-white">취소</button>
            <button type="submit" disabled={isSubmitting} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50">
              {isSubmitting && <Loader2 size={12} className="animate-spin" />} 저장
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function PrototypeTagsTable() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editTag, setEditTag] = useState<PrototypeTag | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const { data, isLoading, error } = usePrototypeTags();
  const deleteMutation = useDeletePrototypeTag();

  const handleDelete = async (id: string) => {
    try { await deleteMutation.mutateAsync(id); toast.success("삭제되었습니다"); }
    catch { toast.error("삭제에 실패했습니다"); }
    setDeleteConfirm(null);
  };

  const items = data?.items ?? [];

  return (
    <>
      <div className="flex justify-end mb-4">
        <button type="button" onClick={() => { setEditTag(null); setDrawerOpen(true); }}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-500">
          <Plus size={12} /> 새 태그
        </button>
      </div>
      {isLoading && <div className="py-12 text-center text-xs text-slate-500">로딩 중...</div>}
      {error && <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-400"><AlertCircle size={14} />{error.message}</div>}
      {!isLoading && !error && (
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                <th className="px-4 py-3 text-left font-medium text-slate-400">Slug</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">레이블</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">한국어</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">컬러</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">순서</th>
                <th className="px-4 py-3 text-left font-medium text-slate-400">상태</th>
                <th className="px-4 py-3 text-right font-medium text-slate-400">액션</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan={7} className="py-12 text-center text-slate-600">태그가 없습니다</td></tr>
              ) : items.map(tag => (
                <tr key={tag.id} className="border-b border-white/5 hover:bg-white/3">
                  <td className="px-4 py-3 font-mono text-slate-400">{tag.slug}</td>
                  <td className="px-4 py-3 text-white">{tag.label}</td>
                  <td className="px-4 py-3 text-slate-400">{tag.label_ko}</td>
                  <td className="px-4 py-3">
                    {tag.color && <span className="flex items-center gap-1.5">
                      <span className="inline-block w-3 h-3 rounded-full" style={{ background: tag.color }} />
                      <span className="text-slate-400">{tag.color}</span>
                    </span>}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-center">{tag.sort_order}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${tag.is_active ? "bg-green-500/20 text-green-400" : "bg-slate-500/20 text-slate-500"}`}>
                      {tag.is_active ? "활성" : "비활성"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button type="button" onClick={() => { setEditTag(tag); setDrawerOpen(true); }} className="rounded p-1.5 text-slate-500 hover:text-white hover:bg-white/10">
                        <Pencil size={12} />
                      </button>
                      {deleteConfirm === tag.id ? (
                        <div className="flex items-center gap-1">
                          <button type="button" onClick={() => handleDelete(tag.id)} className="rounded px-2 py-1 text-xs bg-red-600 text-white hover:bg-red-500">삭제</button>
                          <button type="button" onClick={() => setDeleteConfirm(null)} className="rounded px-2 py-1 text-xs text-slate-500 hover:text-white">취소</button>
                        </div>
                      ) : (
                        <button type="button" onClick={() => setDeleteConfirm(tag.id)} className="rounded p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10">
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <TagEditorDrawer tag={editTag} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
