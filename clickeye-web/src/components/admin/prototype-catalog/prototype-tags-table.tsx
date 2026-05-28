"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, AlertCircle, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
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

const INPUT = "w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-zinc-400 focus:outline-none";

function TagEditorDrawer({ tag, open, onClose }: { tag: PrototypeTag | null; open: boolean; onClose: () => void }) {
  const [form, setForm] = useState<TagFormState>(tagToForm(null));
  const createMutation = useCreatePrototypeTag();
  const updateMutation = useUpdatePrototypeTag();
  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  const tT = useTranslations("toast.prototypeCatalog");

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
        toast.success(tT("tagUpdateSuccess"));
      } else {
        await createMutation.mutateAsync(payload);
        toast.success(tT("tagCreateSuccess"));
      }
      onClose();
    } catch { toast.error(tT("saveFail")); }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} role="button" tabIndex={0} onKeyDown={e => e.key === "Escape" && onClose()} aria-label="닫기" />
      <div className="relative w-full max-w-md h-full overflow-y-auto border-l border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-6 py-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">{tag ? "태그 편집" : "새 태그"}</h2>
          <button type="button" onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">
          <div><label className="text-xs text-[var(--text-muted)] mb-1 block">Slug *</label>
            <input className={INPUT} value={form.slug} onChange={set("slug")} required disabled={!!tag} /></div>
          <div><label className="text-xs text-[var(--text-muted)] mb-1 block">레이블 (영문) *</label>
            <input className={INPUT} value={form.label} onChange={set("label")} required /></div>
          <div><label className="text-xs text-[var(--text-muted)] mb-1 block">레이블 (한국어)</label>
            <input className={INPUT} value={form.label_ko} onChange={set("label_ko")} /></div>
          <div><label className="text-xs text-[var(--text-muted)] mb-1 block">설명</label>
            <input className={INPUT} value={form.description} onChange={set("description")} /></div>
          <div><label className="text-xs text-[var(--text-muted)] mb-1 block">컬러 코드 (예: #3B82F6)</label>
            <input className={INPUT} value={form.color} onChange={set("color")} /></div>
          <div><label className="text-xs text-[var(--text-muted)] mb-1 block">정렬 순서</label>
            <input type="number" className={INPUT} value={form.sort_order} onChange={set("sort_order")} /></div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.is_active} onChange={e => setForm(prev => ({ ...prev, is_active: e.target.checked }))} />
            <span className="text-xs text-[var(--text-secondary)]">활성</span>
          </label>
          <div className="flex justify-end gap-3 pt-4 border-t border-[var(--border-subtle)]">
            <button type="button" onClick={onClose} className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]">취소</button>
            <button type="submit" disabled={isSubmitting} className="flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50">
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
  const tT = useTranslations("toast.prototypeCatalog");

  const handleDelete = async (id: string) => {
    try { await deleteMutation.mutateAsync(id); toast.success(tT("deleteSuccess")); }
    catch { toast.error(tT("deleteFail")); }
    setDeleteConfirm(null);
  };

  const items = data?.items ?? [];

  return (
    <>
      <div className="flex justify-end mb-4">
        <button type="button" onClick={() => { setEditTag(null); setDrawerOpen(true); }}
          className="flex items-center gap-2 rounded-lg bg-zinc-900 px-3 py-2 text-xs font-medium text-white hover:bg-zinc-800">
          <Plus size={12} /> 새 태그
        </button>
      </div>
      {isLoading && <div className="py-12 text-center text-xs text-[var(--text-muted)]">로딩 중...</div>}
      {error && <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-700"><AlertCircle size={14} />{error.message}</div>}
      {!isLoading && !error && (
        <div className="rounded-xl border border-[var(--border-subtle)] overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                <th className="px-4 py-3 text-left font-medium text-[var(--text-muted)]">Slug</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--text-muted)]">레이블</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--text-muted)]">한국어</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--text-muted)]">컬러</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--text-muted)]">순서</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--text-muted)]">상태</th>
                <th className="px-4 py-3 text-right font-medium text-[var(--text-muted)]">액션</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan={7} className="py-12 text-center text-[var(--text-muted)]">태그가 없습니다</td></tr>
              ) : items.map(tag => (
                <tr key={tag.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-hover)]">
                  <td className="px-4 py-3 font-mono text-[var(--text-secondary)]">{tag.slug}</td>
                  <td className="px-4 py-3 text-[var(--text-primary)]">{tag.label}</td>
                  <td className="px-4 py-3 text-[var(--text-secondary)]">{tag.label_ko}</td>
                  <td className="px-4 py-3">
                    {tag.color && <span className="flex items-center gap-1.5">
                      <span className="inline-block w-3 h-3 rounded-full" style={{ background: tag.color }} />
                      <span className="text-[var(--text-secondary)]">{tag.color}</span>
                    </span>}
                  </td>
                  <td className="px-4 py-3 text-[var(--text-secondary)] text-center">{tag.sort_order}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${tag.is_active ? "bg-emerald-50 text-emerald-700" : "bg-zinc-100 text-[var(--text-muted)]"}`}>
                      {tag.is_active ? "활성" : "비활성"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button type="button" onClick={() => { setEditTag(tag); setDrawerOpen(true); }} className="rounded p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]">
                        <Pencil size={12} />
                      </button>
                      {deleteConfirm === tag.id ? (
                        <div className="flex items-center gap-1">
                          <button type="button" onClick={() => handleDelete(tag.id)} className="rounded px-2 py-1 text-xs bg-red-600 text-white hover:bg-red-500">삭제</button>
                          <button type="button" onClick={() => setDeleteConfirm(null)} className="rounded px-2 py-1 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]">취소</button>
                        </div>
                      ) : (
                        <button type="button" onClick={() => setDeleteConfirm(tag.id)} className="rounded p-1.5 text-[var(--text-muted)] hover:text-red-700 hover:bg-red-50">
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
