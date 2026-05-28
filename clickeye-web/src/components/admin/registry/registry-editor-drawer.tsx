"use client";

import { useState } from "react";
import { X, Check } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import {
  type RegistryItemResponse,
  type RegistryItemCreateRequest,
  type RegistryItemUpdateRequest,
} from "@/lib/api-client";
import type { RegistryAdminType } from "@/hooks/use-registry-admin";
import { useCreateRegistryItem, useUpdateRegistryItem } from "@/hooks/use-registry-admin";
import { TagInput } from "@/components/admin/pm/tag-input";

const TYPE_LABELS: Record<RegistryAdminType, string> = {
  agents: "에이전트",
  skills: "스킬",
  hooks: "훅",
  mcps: "MCP 서버",
};

interface FormState {
  name: string;
  slug: string;
  description: string;
  body_md: string;
  version: string;
  category: string;
  is_public: boolean;
  tags: string[];
  domains: string[];
  compatible_pm_specialties: string[];
}

function itemToForm(item: RegistryItemResponse): FormState {
  return {
    name: item.name,
    slug: item.slug,
    description: item.description ?? "",
    body_md: item.body_md ?? "",
    version: item.version,
    category: item.category ?? "",
    is_public: item.is_public,
    tags: item.tags ?? [],
    domains: item.domains ?? [],
    compatible_pm_specialties: item.compatible_pm_specialties ?? [],
  };
}

const EMPTY_FORM: FormState = {
  name: "",
  slug: "",
  description: "",
  body_md: "",
  version: "0.1.0",
  category: "",
  is_public: true,
  tags: [],
  domains: [],
  compatible_pm_specialties: [],
};

interface DrawerFormProps {
  type: RegistryAdminType;
  item: RegistryItemResponse | null;
  onClose: () => void;
}

function DrawerForm({ type, item, onClose }: DrawerFormProps) {
  const isEdit = item !== null;
  const createMutation = useCreateRegistryItem(type);
  const updateMutation = useUpdateRegistryItem(type);
  const isPending = createMutation.isPending || updateMutation.isPending;
  const tT = useTranslations("toast.registry");

  const [form, setForm] = useState<FormState>(item ? itemToForm(item) : EMPTY_FORM);

  function handleSubmit() {
    if (isEdit && item) {
      const data: RegistryItemUpdateRequest = {
        name: form.name,
        description: form.description || null,
        body_md: form.body_md || null,
        version: form.version,
        category: form.category || null,
        is_public: form.is_public,
        tags: form.tags,
        domains: form.domains,
        compatible_pm_specialties: form.compatible_pm_specialties,
      };
      updateMutation.mutate(
        { id: item.id, data },
        {
          onSuccess: () => {
            toast.success(tT("updateSuccess"));
            onClose();
          },
          onError: (e: Error) => toast.error(e.message),
        },
      );
    } else {
      const data: RegistryItemCreateRequest = {
        name: form.name,
        slug: form.slug,
        description: form.description || null,
        body_md: form.body_md || null,
        version: form.version || "0.1.0",
        category: form.category || null,
        is_public: form.is_public,
        config_schema: {},
        tags: form.tags,
        domains: form.domains,
        compatible_pm_specialties: form.compatible_pm_specialties,
      };
      createMutation.mutate(data, {
        onSuccess: () => {
          toast.success(tT("addSuccess"));
          onClose();
        },
        onError: (e: Error) => toast.error(e.message),
      });
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* 헤더 */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-6 py-4">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">
          {TYPE_LABELS[type]} {isEdit ? "편집" : "추가"}
        </h2>
        <button
          type="button"
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          aria-label="닫기"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* 폼 본문 (스크롤 가능) */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">
              이름 <span className="text-red-600">*</span>
            </label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none"
              placeholder="예: Claude Code 에이전트"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">
              Slug {!isEdit && <span className="text-red-600">*</span>}
            </label>
            <input
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
              disabled={isEdit}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none disabled:opacity-50"
              placeholder="예: claude-code"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">버전</label>
            <input
              value={form.version}
              onChange={(e) => setForm({ ...form, version: e.target.value })}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none"
              placeholder="0.1.0"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">카테고리</label>
            <input
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none"
              placeholder="예: ai, automation"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1.5">설명</label>
          <input
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none"
            placeholder="한 줄 설명"
          />
        </div>

        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1.5">
            body_md{" "}
            <span className="text-[var(--text-muted)]">(Markdown 상세 설명)</span>
          </label>
          <textarea data-gramm="false" data-gramm_editor="false"
            rows={12}
            value={form.body_md}
            onChange={(e) => setForm({ ...form, body_md: e.target.value })}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-zinc-50 px-3 py-2 font-mono text-sm text-[var(--text-secondary)] focus:border-zinc-400 focus:outline-none"
            placeholder={"# 마크다운 형식으로 작성\n## 기능\n- 기능 1\n- 기능 2"}
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            id="drawer_is_public"
            type="checkbox"
            checked={form.is_public}
            onChange={(e) => setForm({ ...form, is_public: e.target.checked })}
            className="h-4 w-4 rounded border-[var(--border-medium)]"
          />
          <label htmlFor="drawer_is_public" className="text-sm text-[var(--text-secondary)]">
            공개 (일반 사용자에게 표시)
          </label>
        </div>

        {/* 메타데이터 */}
        <div className="space-y-4 rounded-xl border border-[var(--border-subtle)] p-4">
          <p className="text-xs font-medium text-[var(--text-muted)]">메타데이터 (추천 알고리즘 활용)</p>
          <TagInput
            label="태그"
            values={form.tags}
            onChange={(v) => setForm({ ...form, tags: v })}
            placeholder="예: project-management, automation"
          />
          <TagInput
            label="도메인"
            values={form.domains}
            onChange={(v) => setForm({ ...form, domains: v })}
            placeholder="예: fintech, ecommerce, healthcare"
          />
          <TagInput
            label="호환 PM 전문분야"
            values={form.compatible_pm_specialties}
            onChange={(v) => setForm({ ...form, compatible_pm_specialties: v })}
            placeholder="예: fullstack, backend, frontend"
          />
        </div>
      </div>

      {/* 푸터 액션 */}
      <div className="flex items-center gap-3 border-t border-[var(--border-subtle)] px-6 py-4">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isPending || !form.name || (!isEdit && !form.slug)}
          className="flex items-center gap-2 rounded-xl bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          <Check className="h-4 w-4" />
          {isPending ? (isEdit ? "저장 중..." : "추가 중...") : isEdit ? "저장" : "추가"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-xl border border-[var(--border-subtle)] px-5 py-2.5 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
        >
          취소
        </button>
      </div>
    </div>
  );
}

export interface RegistryEditorDrawerProps {
  type: RegistryAdminType;
  item: RegistryItemResponse | null;
  open: boolean;
  onClose: () => void;
  initialData: RegistryItemCreateRequest;
}

export function RegistryEditorDrawer({
  type,
  item,
  open,
  onClose,
}: RegistryEditorDrawerProps) {
  return (
    <>
      {/* 배경 오버레이 */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40"
          onClick={onClose}
          onKeyDown={(e) => e.key === "Escape" && onClose()}
          role="button"
          tabIndex={0}
          aria-label="닫기"
        />
      )}

      {/* 드로어 */}
      <div
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-lg transform bg-[var(--bg-surface)] shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label={`${TYPE_LABELS[type]} ${item ? "편집" : "추가"}`}
      >
        {/* open 시에만 마운트하여 매 오픈마다 폼 상태를 초기화 */}
        {open && (
          <DrawerForm
            key={item?.id ?? "new"}
            type={type}
            item={item}
            onClose={onClose}
          />
        )}
      </div>
    </>
  );
}
