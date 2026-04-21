"use client";

import { useState } from "react";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { useAppSettings, useSetVariantCount, useSetRagTopK } from "@/hooks/use-app-settings";

const INPUT = "rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-xs text-white focus:border-blue-500 focus:outline-none w-24 text-center";

export function AppSettingsPanel() {
  const { data: settings, isLoading } = useAppSettings();
  const setVariantCount = useSetVariantCount();
  const setRagTopK = useSetRagTopK();

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

  if (isLoading) return <div className="py-8 text-center text-xs text-slate-500">로딩 중...</div>;

  return (
    <div className="space-y-4 max-w-lg">
      {/* Variant Count */}
      <div className="rounded-xl border border-white/10 bg-slate-900 p-6">
        <h3 className="text-sm font-semibold text-white mb-1">프로토타입 제안 개수</h3>
        <p className="text-xs text-slate-500 mb-4">
          위저드에서 사용자에게 제안할 프로토타입 variant 수 (2–5, 기본: 3)
        </p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setVariantCountLocal(v => Math.max(2, (v ?? currentVariantCount) - 1))}
            className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white hover:border-white/30"
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
            className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white hover:border-white/30"
          >
            +
          </button>
          <button
            type="button"
            onClick={handleSaveVariantCount}
            disabled={setVariantCount.isPending}
            className="flex items-center gap-2 ml-4 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {setVariantCount.isPending ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            저장
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-600">현재 DB 값: {getSettingValue("prototype_variant_count")}</p>
      </div>

      {/* RAG top-k */}
      <div className="rounded-xl border border-white/10 bg-slate-900 p-6">
        <h3 className="text-sm font-semibold text-white mb-1">Claude RAG top-k</h3>
        <p className="text-xs text-slate-500 mb-4">
          AI 프로토타입 생성 시 참조할 카탈로그 엔트리 수 (1–20, 기본: 8)
        </p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setRagTopKLocal(v => Math.max(1, (v ?? currentRagTopK) - 1))}
            className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white hover:border-white/30"
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
            className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:text-white hover:border-white/30"
          >
            +
          </button>
          <button
            type="button"
            onClick={handleSaveRagTopK}
            disabled={setRagTopK.isPending}
            className="flex items-center gap-2 ml-4 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {setRagTopK.isPending ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            저장
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-600">현재 DB 값: {getSettingValue("prototype_rag_top_k")}</p>
      </div>
    </div>
  );
}
