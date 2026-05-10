"use client";

import { useState } from "react";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { useAppSettings, useSetVariantCount, useSetRagTopK, useSetLivePreviewEnabled } from "@/hooks/use-app-settings";

const INPUT = "rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none w-24 text-center";

export function AppSettingsPanel() {
  const { data: settings, isLoading } = useAppSettings();
  const setVariantCount = useSetVariantCount();
  const setRagTopK = useSetRagTopK();
  const setLivePreviewEnabled = useSetLivePreviewEnabled();

  const [variantCount, setVariantCountLocal] = useState<number | null>(null);
  const [ragTopK, setRagTopKLocal] = useState<number | null>(null);

  const getSettingValue = (key: string): number => {
    const s = settings?.find(s => s.key === key);
    if (!s) return key === "prototype_variant_count" ? 3 : 8;
    const v = s.value;
    if (typeof v === "number") return v;
    if (typeof v === "object" && v !== null && "value" in v) return (v as { value: number }).value;
    return 0;
  };

  const getLivePreviewEnabled = (): boolean => {
    const s = settings?.find(s => s.key === "live_preview_enabled");
    if (!s) return true;
    const v = s.value;
    if (typeof v === "boolean") return v;
    if (typeof v === "object" && v !== null && "value" in v) return Boolean((v as { value: unknown }).value);
    return true;
  };

  const handleToggleLivePreview = async () => {
    const next = !getLivePreviewEnabled();
    try {
      await setLivePreviewEnabled.mutateAsync(next);
      toast.success(`라이브 프리뷰가 ${next ? "활성화" : "비활성화"}되었습니다`);
    } catch { toast.error("저장에 실패했습니다"); }
  };

  const currentVariantCount = variantCount ?? (isLoading ? 3 : getSettingValue("prototype_variant_count"));
  const currentRagTopK = ragTopK ?? (isLoading ? 8 : getSettingValue("prototype_rag_top_k"));

  const handleSaveVariantCount = async () => {
    try {
      await setVariantCount.mutateAsync(currentVariantCount);
      toast.success("프로토타입 variant 개수가 저장되었습니다");
    } catch { toast.error("저장에 실패했습니다"); }
  };

  const handleSaveRagTopK = async () => {
    try {
      await setRagTopK.mutateAsync(currentRagTopK);
      toast.success("RAG top-k가 저장되었습니다");
    } catch { toast.error("저장에 실패했습니다"); }
  };

  if (isLoading) return <div className="py-8 text-center text-xs text-[var(--text-muted)]">로딩 중...</div>;

  return (
    <div className="space-y-4 max-w-lg">
      {/* Variant Count */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">프로토타입 제안 개수</h3>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          위저드에서 사용자에게 제안할 프로토타입 variant 수 (2–5, 기본: 3)
        </p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setVariantCountLocal(v => Math.max(2, (v ?? currentVariantCount) - 1))}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-medium)]"
          >
            −
          </button>
          <input
            type="number"
            min={2}
            max={5}
            value={currentVariantCount}
            onChange={e => setVariantCountLocal(Math.max(2, Math.min(5, parseInt(e.target.value, 10) || 3)))}
            className={INPUT}
          />
          <button
            type="button"
            onClick={() => setVariantCountLocal(v => Math.min(5, (v ?? currentVariantCount) + 1))}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-medium)]"
          >
            +
          </button>
          <button
            type="button"
            onClick={handleSaveVariantCount}
            disabled={setVariantCount.isPending}
            className="flex items-center gap-2 ml-4 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            {setVariantCount.isPending ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            저장
          </button>
        </div>
        <p className="mt-2 text-xs text-[var(--text-muted)]">현재 DB 값: {getSettingValue("prototype_variant_count")}</p>
      </div>

      {/* Live Preview Toggle */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">라이브 프리뷰</h3>
            <p className="text-xs text-[var(--text-muted)]">
              위저드 솔루션 분석 기능. 서버 API 키를 소비합니다 — 비용 제어를 위해 OFF로 설정 가능합니다.
            </p>
          </div>
          <button
            type="button"
            onClick={handleToggleLivePreview}
            disabled={setLivePreviewEnabled.isPending}
            aria-label={getLivePreviewEnabled() ? "라이브 프리뷰 비활성화" : "라이브 프리뷰 활성화"}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors focus:outline-none disabled:opacity-50 ${
              getLivePreviewEnabled() ? "bg-emerald-500" : "bg-zinc-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
                getLivePreviewEnabled() ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
        <p className="mt-3 text-xs text-[var(--text-muted)]">
          현재: <span className={getLivePreviewEnabled() ? "text-emerald-600 font-medium" : "text-zinc-500"}>
            {getLivePreviewEnabled() ? "활성화" : "비활성화"}
          </span>
        </p>
      </div>

      {/* RAG top-k */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Claude RAG top-k</h3>
        <p className="text-xs text-[var(--text-muted)] mb-4">
          AI 프로토타입 생성 시 참조할 카탈로그 엔트리 수 (1–20, 기본: 8)
        </p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setRagTopKLocal(v => Math.max(1, (v ?? currentRagTopK) - 1))}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-medium)]"
          >
            −
          </button>
          <input
            type="number"
            min={1}
            max={20}
            value={currentRagTopK}
            onChange={e => setRagTopKLocal(Math.max(1, Math.min(20, parseInt(e.target.value, 10) || 8)))}
            className={INPUT}
          />
          <button
            type="button"
            onClick={() => setRagTopKLocal(v => Math.min(20, (v ?? currentRagTopK) + 1))}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-medium)]"
          >
            +
          </button>
          <button
            type="button"
            onClick={handleSaveRagTopK}
            disabled={setRagTopK.isPending}
            className="flex items-center gap-2 ml-4 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            {setRagTopK.isPending ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            저장
          </button>
        </div>
        <p className="mt-2 text-xs text-[var(--text-muted)]">현재 DB 값: {getSettingValue("prototype_rag_top_k")}</p>
      </div>
    </div>
  );
}
