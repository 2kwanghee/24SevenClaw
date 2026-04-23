"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, AlertCircle, Eye } from "lucide-react";
import { toast } from "sonner";

import {
  type RegistryItemResponse,
  type RegistryItemCreateRequest,
} from "@/lib/api-client";
import type { RegistryAdminType } from "@/hooks/use-registry-admin";
import {
  useRegistryItems,
  useDeleteRegistryItem,
} from "@/hooks/use-registry-admin";
import { RegistryEditorDrawer } from "./registry-editor-drawer";

const TYPE_LABELS: Record<RegistryAdminType, string> = {
  agents: "에이전트",
  skills: "스킬",
  hooks: "훅",
  mcps: "MCP 서버",
};

const INITIAL_FORM: RegistryItemCreateRequest = {
  name: "",
  slug: "",
  description: "",
  body_md: "",
  version: "0.1.0",
  category: "",
  is_public: true,
  config_schema: {},
};

interface BodyMdModalProps {
  content: string;
  onClose: () => void;
}

function BodyMdModal({ content, onClose }: BodyMdModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        role="button"
        tabIndex={0}
        aria-label="닫기"
      />
      <div className="relative w-full max-w-2xl mx-4 rounded-xl border border-white/10 bg-slate-900 p-6">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-slate-500 hover:text-white"
          aria-label="닫기"
        >
          ✕
        </button>
        <h3 className="mb-3 text-sm font-semibold text-white">body_md</h3>
        <pre className="max-h-[60vh] overflow-auto rounded-lg bg-black/40 p-4 font-mono text-xs text-slate-300 whitespace-pre-wrap">
          {content || "(비어 있음)"}
        </pre>
      </div>
    </div>
  );
}

export interface RegistryListTableProps {
  type: RegistryAdminType;
}

export function RegistryListTable({ type }: RegistryListTableProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<RegistryItemResponse | null>(null);
  const [bodyMdPreview, setBodyMdPreview] = useState<string | null>(null);

  const { data, isLoading, error } = useRegistryItems(type, { limit: 200 });
  const deleteMutation = useDeleteRegistryItem(type);

  const items = data?.items ?? [];

  function openAdd() {
    setEditingItem(null);
    setDrawerOpen(true);
  }

  function openEdit(item: RegistryItemResponse) {
    setEditingItem(item);
    setDrawerOpen(true);
  }

  if (isLoading) {
    return <div className="py-12 text-center text-sm text-slate-500">불러오는 중...</div>;
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {(error as Error).message}
      </div>
    );
  }

  return (
    <>
      {bodyMdPreview !== null && (
        <BodyMdModal content={bodyMdPreview} onClose={() => setBodyMdPreview(null)} />
      )}

      <RegistryEditorDrawer
        type={type}
        item={editingItem}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setEditingItem(null);
        }}
        initialData={INITIAL_FORM}
      />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={openAdd}
          className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500"
        >
          <Plus className="h-4 w-4" />
          {TYPE_LABELS[type]} 추가
        </button>
      </div>

      {items.length === 0 ? (
        <div className="py-12 text-center text-sm text-slate-600">항목이 없습니다.</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/10">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">이름</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Slug</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">카테고리</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">버전</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">공개</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-400">액션</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-4 py-3">
                    <div className="text-sm text-white">{item.name}</div>
                    {item.description && (
                      <div className="max-w-[200px] truncate text-xs text-slate-500">
                        {item.description}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-sm text-slate-400">{item.slug}</td>
                  <td className="px-4 py-3 text-sm text-slate-400">{item.category ?? "—"}</td>
                  <td className="px-4 py-3 text-sm text-slate-400">{item.version}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{item.is_public ? "✓" : "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {item.body_md && (
                        <button
                          type="button"
                          onClick={() => setBodyMdPreview(item.body_md)}
                          className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 transition-colors hover:bg-white/5"
                          aria-label="body_md 미리보기"
                        >
                          <Eye className="h-3 w-3" />
                          MD
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => openEdit(item)}
                        className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 transition-colors hover:bg-white/5"
                        aria-label={`${item.name} 편집`}
                      >
                        <Pencil className="h-3 w-3" />
                        편집
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (!confirm(`"${item.name}" 항목을 삭제하시겠습니까?`)) return;
                          deleteMutation.mutate(item.id, {
                            onSuccess: () => toast.success("항목이 삭제되었습니다."),
                            onError: (e: Error) => toast.error(e.message),
                          });
                        }}
                        disabled={deleteMutation.isPending}
                        className="inline-flex items-center gap-1 rounded-lg border border-red-500/20 px-2.5 py-1 text-xs text-red-400 transition-colors hover:bg-red-500/10 disabled:opacity-50"
                        aria-label={`${item.name} 삭제`}
                      >
                        <Trash2 className="h-3 w-3" />
                        삭제
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
