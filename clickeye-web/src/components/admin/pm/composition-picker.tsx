"use client";

import { useState, useMemo } from "react";
import { Search, X, Check } from "lucide-react";

import {
  useCatalogAgents,
  useCatalogSkills,
  useCatalogHooks,
  useCatalogMCPs,
} from "@/hooks/use-catalog";

export type PickableComponentType = "agent" | "skill" | "hook" | "mcp_server";

interface PickerItem {
  slug: string;
  name: string;
  description: string | null;
  category?: string | null;
}

export interface PickerSelection {
  slug: string;
  name: string;
}

interface CompositionPickerProps {
  componentType: PickableComponentType;
  /** 이미 추가된 슬러그 목록 — 비활성화 표시 */
  existingSlugs: string[];
  onConfirm: (items: PickerSelection[]) => void;
  onClose: () => void;
}

function useRegistryItems(componentType: PickableComponentType): {
  items: PickerItem[];
  isLoading: boolean;
} {
  const agents = useCatalogAgents();
  const skills = useCatalogSkills();
  const hooks = useCatalogHooks();
  const mcps = useCatalogMCPs();

  const map: Record<PickableComponentType, { items: PickerItem[]; isLoading: boolean }> = {
    agent: {
      items: (agents.data?.items ?? []).map((a) => ({ slug: a.id, name: a.label, description: a.description })),
      isLoading: agents.isLoading,
    },
    skill: {
      items: (skills.data?.items ?? []).map((s) => ({ slug: s.id, name: s.label, description: s.description, category: s.category })),
      isLoading: skills.isLoading,
    },
    hook: {
      items: (hooks.data?.items ?? []).map((h) => ({ slug: h.id, name: h.label, description: h.description, category: h.category })),
      isLoading: hooks.isLoading,
    },
    mcp_server: {
      items: (mcps.data?.items ?? []).map((m) => ({ slug: m.id, name: m.label, description: m.description, category: m.category })),
      isLoading: mcps.isLoading,
    },
  };

  return map[componentType];
}

export function CompositionPicker({
  componentType,
  existingSlugs,
  onConfirm,
  onClose,
}: CompositionPickerProps) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const { items, isLoading } = useRegistryItems(componentType);

  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(
      (item) =>
        item.slug.toLowerCase().includes(q) ||
        item.name.toLowerCase().includes(q) ||
        (item.description ?? "").toLowerCase().includes(q),
    );
  }, [items, query]);

  function toggle(item: PickerItem) {
    if (existingSlugs.includes(item.slug)) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(item.slug)) next.delete(item.slug);
      else next.add(item.slug);
      return next;
    });
  }

  function handleConfirm() {
    const selections = items
      .filter((item) => selected.has(item.slug))
      .map((item) => ({ slug: item.slug, name: item.name }));
    onConfirm(selections);
  }

  return (
    <div className="rounded-xl border border-[var(--border-medium)] bg-[var(--bg-surface)] shadow-lg">
      {/* 검색 헤더 */}
      <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] px-3 py-2">
        <Search className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="이름 또는 슬러그 검색..."
          className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
        />
        <button
          type="button"
          onClick={onClose}
          className="text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          aria-label="닫기"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* 항목 목록 */}
      <div className="max-h-56 overflow-y-auto">
        {isLoading && (
          <p className="px-4 py-3 text-sm text-[var(--text-muted)]">불러오는 중...</p>
        )}
        {!isLoading && filtered.length === 0 && (
          <p className="px-4 py-3 text-sm text-[var(--text-muted)]">검색 결과가 없습니다.</p>
        )}
        {filtered.map((item) => {
          const alreadyAdded = existingSlugs.includes(item.slug);
          const isChecked = selected.has(item.slug);
          return (
            <button
              key={item.slug}
              type="button"
              onClick={() => toggle(item)}
              disabled={alreadyAdded}
              className={[
                "flex w-full items-start gap-3 px-4 py-2.5 text-left",
                alreadyAdded
                  ? "cursor-not-allowed opacity-40"
                  : "hover:bg-[var(--bg-hover)]",
              ].join(" ")}
            >
              {/* 체크박스 */}
              <div className={[
                "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                isChecked
                  ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-fg)]"
                  : "border-[var(--border-medium)] bg-transparent",
                alreadyAdded ? "border-[var(--border-medium)] bg-[var(--bg-base)]" : "",
              ].join(" ")}>
                {(isChecked || alreadyAdded) && <Check className="h-2.5 w-2.5" />}
              </div>
              {/* 항목 정보 */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-[var(--text-muted)]">{item.slug}</span>
                  {item.category && (
                    <span className="rounded-full border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--text-muted)]">
                      {item.category}
                    </span>
                  )}
                  {alreadyAdded && (
                    <span className="text-[10px] text-[var(--text-muted)]">이미 추가됨</span>
                  )}
                </div>
                <span className="text-sm font-medium text-[var(--text-primary)]">{item.name}</span>
                {item.description && (
                  <span className="line-clamp-1 text-xs text-[var(--text-secondary)]">{item.description}</span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* 하단 확정 버튼 */}
      <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-4 py-2.5">
        <span className="text-xs text-[var(--text-muted)]">
          {selected.size > 0 ? `${selected.size}개 선택됨` : "항목을 선택하세요"}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={selected.size === 0}
            className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-[var(--accent-fg)] hover:opacity-90 disabled:opacity-40"
          >
            추가 ({selected.size})
          </button>
        </div>
      </div>
    </div>
  );
}
