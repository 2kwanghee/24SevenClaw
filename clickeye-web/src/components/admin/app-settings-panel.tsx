"use client";

import { useState } from "react";
import { Loader2, Save } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAppSettings, useSetVariantCount, useSetRagTopK } from "@/hooks/use-app-settings";

const INPUT = "rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-xs text-[var(--text-primary)] focus:border-zinc-400 focus:outline-none w-24 text-center";

export function AppSettingsPanel() {
  const { data: settings, isLoading } = useAppSettings();
  const setVariantCount = useSetVariantCount();
  const setRagTopK = useSetRagTopK();
  const [variantCount, setVariantCountLocal] = useState<number | null>(null);
  const [ragTopK, setRagTopKLocal] = useState<number | null>(null);
  const tT = useTranslations("toast.appSettings");
  const tG = useTranslations("toast.generic");

  const getSettingValue = (key: string): number => {
    const s = settings?.find(s => s.key === key);
    if (!s) return key === "prototype_variant_count" ? 3 : 8;
    const v = s.value;
    if (typeof v === "number") return v;
    if (typeof v === "object" && v !== null && "value" in v) return (v as { value: number }).value;
    return 0;
  };

  const currentVariantCount = variantCount ?? (isLoading ? 3 : getSettingValue("prototype_variant_count"));
  const currentRagTopK = ragTopK ?? (isLoading ? 8 : getSettingValue("prototype_rag_top_k"));

  const handleSaveVariantCount = async () => {
    try {
      await setVariantCount.mutateAsync(currentVariantCount);
      toast.success(tT("prototypeVariantSaveSuccess"));
    } catch { toast.error(tG("saveFail")); }
  };

  const handleSaveRagTopK = async () => {
    try {
      await setRagTopK.mutateAsync(currentRagTopK);
      toast.success(tT("ragTopKSaveSuccess"));
    } catch { toast.error(tG("saveFail")); }
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
