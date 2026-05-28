"use client";

import { useState } from "react";
import { Plus, Trash2, AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { pmProfiles, type PMCompositionResponse } from "@/lib/api-client";
import { useDeleteComposition } from "@/hooks/use-pm-admin";
import { CompositionPicker, type PickableComponentType, type PickerSelection } from "@/components/admin/pm/composition-picker";

type ComponentType = "agent" | "skill" | "hook" | "mcp_server";

const SECTIONS: { type: ComponentType; label: string }[] = [
  { type: "agent",      label: "AI 에이전트" },
  { type: "skill",      label: "스킬" },
  { type: "mcp_server", label: "MCP 서버" },
  { type: "hook",       label: "Hook" },
];

const TYPE_COLORS: Record<ComponentType, string> = {
  agent:      "border-blue-200 bg-blue-50 text-blue-800",
  skill:      "border-emerald-200 bg-emerald-50 text-emerald-800",
  mcp_server: "border-purple-200 bg-purple-50 text-purple-800",
  hook:       "border-amber-200 bg-amber-50 text-amber-800",
};

interface CompositionChipProps {
  item: PMCompositionResponse;
  onDelete: () => void;
  isDeleting: boolean;
}

function CompositionChip({ item, onDelete, isDeleting }: CompositionChipProps) {
  const colorClass = TYPE_COLORS[item.component_type as ComponentType] ?? "border-zinc-200 bg-zinc-50 text-zinc-700";
  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${colorClass}`}>
      <span className="font-mono opacity-60">{item.component_slug}</span>
      <span>{item.component_name}</span>
      <button
        type="button"
        onClick={() => {
          if (!confirm(`"${item.component_name}"을(를) 제거하시겠습니까?`)) return;
          onDelete();
        }}
        disabled={isDeleting}
        className="ml-0.5 rounded-full p-0.5 opacity-50 transition-opacity hover:opacity-100 disabled:cursor-not-allowed"
        aria-label={`${item.component_name} 제거`}
      >
        <Trash2 className="h-3 w-3" />
      </button>
    </div>
  );
}

interface SectionProps {
  label: string;
  type: ComponentType;
  items: PMCompositionResponse[];
  profileId: string;
  token: string;
  onBulkAdded: () => void;
}

function CompositionTypeSection({ label, type, items, profileId, token, onBulkAdded }: SectionProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const deleteMutation = useDeleteComposition(profileId);
  const tT = useTranslations("toast.pm");

  const existingSlugs = items.map((i) => i.component_slug);

  async function handleConfirm(selections: PickerSelection[]) {
    if (selections.length === 0) return;
    setPickerOpen(false);
    setAdding(true);
    try {
      await Promise.all(
        selections.map((sel, idx) =>
          pmProfiles.createComposition(token, profileId, {
            component_type: type,
            component_slug: sel.slug,
            component_name: sel.name,
            display_order: items.length + idx,
          }),
        ),
      );
      toast.success(tT("compositionAddSuccess", { count: selections.length }));
      onBulkAdded();
    } catch {
      toast.error(tT("compositionAddFail"));
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 space-y-3">
      {/* 섹션 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[var(--text-primary)]">{label}</span>
          <span className="rounded-full bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-muted)]">
            {items.length}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setPickerOpen(true)}
          disabled={adding}
          className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2.5 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-50"
        >
          <Plus className="h-3 w-3" />
          {adding ? "추가 중..." : "추가"}
        </button>
      </div>

      {/* 칩 목록 */}
      {items.length === 0 ? (
        <p className="text-xs text-[var(--text-muted)]">아직 추가된 항목이 없습니다.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <CompositionChip
              key={item.id}
              item={item}
              isDeleting={deleteMutation.isPending}
              onDelete={() =>
                deleteMutation.mutate(item.id, {
                  onError: (e: Error) => toast.error(e.message),
                })
              }
            />
          ))}
        </div>
      )}

      {/* 피커 팝오버 */}
      {pickerOpen && (
        <div className="relative">
          <CompositionPicker
            componentType={type as PickableComponentType}
            existingSlugs={existingSlugs}
            onConfirm={handleConfirm}
            onClose={() => setPickerOpen(false)}
          />
        </div>
      )}
    </div>
  );
}

export interface CompositionPanelProps {
  profileId: string;
}

export function CompositionPanel({ profileId }: CompositionPanelProps) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["pm-composition", profileId],
    queryFn: () => pmProfiles.getComposition(token, profileId),
    enabled: !!token,
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["pm-composition", profileId] });
  }

  const grouped: Record<ComponentType, PMCompositionResponse[]> = {
    agent:      data?.agents ?? [],
    skill:      data?.skills ?? [],
    mcp_server: data?.mcp_servers ?? [],
    hook:       data?.hooks ?? [],
  };

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold text-[var(--text-primary)]">구성 컴포넌트 (팀)</h2>
      <p className="text-xs text-[var(--text-muted)]">
        레지스트리에 등록된 항목만 추가할 수 있습니다. 각 타입별로 여러 개를 선택할 수 있습니다.
      </p>

      {isLoading && (
        <div className="py-8 text-center text-sm text-[var(--text-muted)]">불러오는 중...</div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {(error as Error).message}
        </div>
      )}

      {!isLoading && !error && SECTIONS.map(({ type, label }) => (
        <CompositionTypeSection
          key={type}
          label={label}
          type={type}
          items={grouped[type]}
          profileId={profileId}
          token={token}
          onBulkAdded={invalidate}
        />
      ))}
    </div>
  );
}
