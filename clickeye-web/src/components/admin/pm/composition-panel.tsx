"use client";

import { useState } from "react";
import { Plus, Trash2, Pencil, X, Check, AlertCircle, ChevronDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { pmProfiles, type PMCompositionResponse, type PMCompositionCreateRequest } from "@/lib/api-client";
import { useUpsertComposition, useDeleteComposition } from "@/hooks/use-pm-admin";

const COMPONENT_TYPES = ["agent", "skill", "hook", "mcp_server", "plugin"] as const;
type ComponentType = typeof COMPONENT_TYPES[number];

const TYPE_LABELS: Record<ComponentType, string> = {
  agent: "Agent",
  skill: "Skill",
  hook: "Hook",
  mcp_server: "MCP 서버",
  plugin: "Plugin",
};

interface CompositionItemRowProps {
  item: PMCompositionResponse;
  onDelete: (id: string) => void;
  onEdit: (item: PMCompositionResponse) => void;
  isDeleting: boolean;
}

function CompositionItemRow({ item, onDelete, onEdit, isDeleting }: CompositionItemRowProps) {
  return (
    <tr className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-hover)]">
      <td className="px-4 py-3 text-sm text-[var(--text-secondary)]">{item.display_order}</td>
      <td className="px-4 py-3">
        <span className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-2 py-0.5 text-xs text-[var(--text-secondary)]">
          {TYPE_LABELS[item.component_type as ComponentType] ?? item.component_type}
        </span>
      </td>
      <td className="px-4 py-3 font-mono text-sm text-[var(--text-primary)]">{item.component_slug}</td>
      <td className="px-4 py-3 text-sm text-[var(--text-primary)]">{item.component_name}</td>
      <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">{item.is_required ? "✓" : "—"}</td>
      <td className="px-4 py-3 text-xs text-[var(--text-muted)] max-w-[160px] truncate">
        {item.config?.body_md_override ? "있음" : "—"}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-1">
          <button
            type="button"
            onClick={() => onEdit(item)}
            className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2.5 py-1 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
            aria-label={`${item.component_name} 편집`}
          >
            <Pencil className="h-3 w-3" />
            편집
          </button>
          <button
            type="button"
            onClick={() => {
              if (!confirm(`"${item.component_name}" 컴포넌트를 삭제하시겠습니까?`)) return;
              onDelete(item.id);
            }}
            disabled={isDeleting}
            className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-2.5 py-1 text-xs text-red-700 transition-colors hover:bg-red-50 disabled:opacity-50"
            aria-label={`${item.component_name} 삭제`}
          >
            <Trash2 className="h-3 w-3" />
            삭제
          </button>
        </div>
      </td>
    </tr>
  );
}

interface EditFormState {
  id?: string;
  component_type: string;
  component_slug: string;
  component_name: string;
  display_order: number;
  is_required: boolean;
  body_md_override: string;
}

function toEditState(item: PMCompositionResponse): EditFormState {
  return {
    id: item.id,
    component_type: item.component_type,
    component_slug: item.component_slug,
    component_name: item.component_name,
    display_order: item.display_order,
    is_required: item.is_required,
    body_md_override: (item.config?.body_md_override as string) ?? "",
  };
}

const EMPTY_EDIT: EditFormState = {
  component_type: "agent",
  component_slug: "",
  component_name: "",
  display_order: 0,
  is_required: false,
  body_md_override: "",
};

function buildConfig(state: EditFormState): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  if (state.body_md_override.trim()) {
    config.body_md_override = state.body_md_override.trim();
  }
  return config;
}

interface CompositionFormPanelProps {
  form: EditFormState;
  onChange: (f: EditFormState) => void;
  onSubmit: () => void;
  onCancel: () => void;
  isPending: boolean;
  isEdit: boolean;
}

function CompositionFormPanel({ form, onChange, onSubmit, onCancel, isPending, isEdit }: CompositionFormPanelProps) {
  const [showBodyMd, setShowBodyMd] = useState(false);

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-5 space-y-4">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">
        {isEdit ? "구성 컴포넌트 편집" : "구성 컴포넌트 추가"}
      </h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">타입</label>
          <select
            value={form.component_type}
            onChange={(e) => onChange({ ...form, component_type: e.target.value })}
            disabled={isEdit}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none disabled:opacity-50"
          >
            {COMPONENT_TYPES.map((t) => (
              <option key={t} value={t}>{TYPE_LABELS[t]}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">Slug</label>
          <input
            value={form.component_slug}
            onChange={(e) => onChange({ ...form, component_slug: e.target.value })}
            disabled={isEdit}
            placeholder="예: code-reviewer"
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none disabled:opacity-50"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">이름</label>
          <input
            value={form.component_name}
            onChange={(e) => onChange({ ...form, component_name: e.target.value })}
            placeholder="예: 코드 리뷰어"
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">표시 순서</label>
          <input
            type="number"
            min={0}
            value={form.display_order}
            onChange={(e) => onChange({ ...form, display_order: parseInt(e.target.value) || 0 })}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none"
          />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input
          id="comp_is_required"
          type="checkbox"
          checked={form.is_required}
          onChange={(e) => onChange({ ...form, is_required: e.target.checked })}
          className="h-4 w-4 rounded border-[var(--border-medium)]"
        />
        <label htmlFor="comp_is_required" className="text-sm text-[var(--text-secondary)]">필수 컴포넌트</label>
      </div>

      {/* body_md_override 섹션 */}
      <div>
        <button
          type="button"
          onClick={() => setShowBodyMd(!showBodyMd)}
          className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
        >
          {showBodyMd ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          body_md_override (마크다운 재정의)
        </button>
        {showBodyMd && (
          <textarea
            rows={8}
            value={form.body_md_override}
            onChange={(e) => onChange({ ...form, body_md_override: e.target.value })}
            placeholder="# 커스텀 마크다운&#10;레지스트리 body_md 대신 이 내용이 사용됩니다."
            className="mt-2 w-full rounded-lg border border-[var(--border-subtle)] bg-zinc-50 px-3 py-2 font-mono text-sm text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none"
          />
        )}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onSubmit}
          disabled={isPending || !form.component_slug || !form.component_name}
          className="flex items-center gap-1.5 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          <Check className="h-3.5 w-3.5" />
          {isPending ? (isEdit ? "저장 중..." : "추가 중...") : (isEdit ? "저장" : "추가")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
        >
          취소
        </button>
      </div>
    </div>
  );
}

export interface CompositionPanelProps {
  profileId: string;
}

export function CompositionPanel({ profileId }: CompositionPanelProps) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const [formState, setFormState] = useState<EditFormState | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["pm-composition", profileId],
    queryFn: () => pmProfiles.getComposition(token, profileId),
    enabled: !!token,
  });

  const upsertMutation = useUpsertComposition(profileId);
  const deleteMutation = useDeleteComposition(profileId);

  const allItems: PMCompositionResponse[] = data
    ? [
        ...data.agents,
        ...data.skills,
        ...data.hooks,
        ...data.mcp_servers,
        ...data.plugins,
      ].sort((a, b) => a.display_order - b.display_order)
    : [];

  function openAdd() {
    setFormState({ ...EMPTY_EDIT });
  }

  function openEdit(item: PMCompositionResponse) {
    setFormState(toEditState(item));
  }

  function handleSubmit() {
    if (!formState) return;
    const config = buildConfig(formState);
    const isEdit = !!formState.id;

    if (isEdit && formState.id) {
      upsertMutation.mutate(
        {
          id: formState.id,
          data: {
            component_name: formState.component_name,
            display_order: formState.display_order,
            is_required: formState.is_required,
            config,
          },
        },
        {
          onSuccess: () => {
            toast.success("구성 컴포넌트가 수정되었습니다.");
            setFormState(null);
          },
          onError: (e: Error) => toast.error(e.message),
        },
      );
    } else {
      upsertMutation.mutate(
        {
          data: {
            component_type: formState.component_type,
            component_slug: formState.component_slug,
            component_name: formState.component_name,
            display_order: formState.display_order,
            is_required: formState.is_required,
            config,
          },
        },
        {
          onSuccess: () => {
            toast.success("구성 컴포넌트가 추가되었습니다.");
            setFormState(null);
          },
          onError: (e: Error) => toast.error(e.message),
        },
      );
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">구성 컴포넌트</h2>
        {!formState && (
          <button
            type="button"
            onClick={openAdd}
            className="flex items-center gap-1.5 rounded-xl bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-800"
          >
            <Plus className="h-3.5 w-3.5" />
            추가
          </button>
        )}
        {formState && (
          <button
            type="button"
            onClick={() => setFormState(null)}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
          >
            <X className="h-3.5 w-3.5" />
            닫기
          </button>
        )}
      </div>

      {formState && (
        <CompositionFormPanel
          form={formState}
          onChange={setFormState}
          onSubmit={handleSubmit}
          onCancel={() => setFormState(null)}
          isPending={upsertMutation.isPending}
          isEdit={!!formState.id}
        />
      )}

      {isLoading && (
        <div className="py-8 text-center text-sm text-[var(--text-muted)]">불러오는 중...</div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {(error as Error).message}
        </div>
      )}

      {!isLoading && allItems.length === 0 && (
        <div className="py-8 text-center text-sm text-[var(--text-muted)]">
          구성 컴포넌트가 없습니다. 위 버튼으로 추가하세요.
        </div>
      )}

      {allItems.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">순서</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">타입</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">Slug</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">이름</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">필수</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">MD 재정의</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">액션</th>
              </tr>
            </thead>
            <tbody>
              {allItems.map((item) => (
                <CompositionItemRow
                  key={item.id}
                  item={item}
                  onEdit={openEdit}
                  onDelete={(id) =>
                    deleteMutation.mutate(id, {
                      onSuccess: () => toast.success("삭제되었습니다."),
                      onError: (e: Error) => toast.error(e.message),
                    })
                  }
                  isDeleting={deleteMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
