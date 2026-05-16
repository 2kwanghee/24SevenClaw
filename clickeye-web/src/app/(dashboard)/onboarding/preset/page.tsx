"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles, ArrowRight, Zap } from "lucide-react";
import { toast } from "sonner";
import { useSession } from "next-auth/react";

import { cn } from "@/lib/utils";
import { usePresets } from "@/hooks/use-presets";
import { PresetCard } from "@/components/presets/preset-card";
import { NaturalLanguageInput } from "@/components/presets/natural-language-input";
import { presets, type PresetResponse, type NaturalLanguageConfigResponse } from "@/lib/api-client";
import { NL_ANALYSIS_STORAGE_KEY } from "@/lib/storage-keys";

export default function PresetSelectionPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const { data, isLoading } = usePresets();
  const [selectedPreset, setSelectedPreset] = useState<PresetResponse | null>(null);
  const [nlResult, setNlResult] = useState<NaturalLanguageConfigResponse | null>(null);
  const [nlText, setNlText] = useState<string>("");
  const [nlLoading, setNlLoading] = useState(false);

  const presetList = data?.items ?? [];

  const handleSelectPreset = (preset: PresetResponse) => {
    setSelectedPreset((prev) => (prev?.id === preset.id ? null : preset));
  };

  const handleApplyAndStart = () => {
    if (!selectedPreset) return;
    router.push("/solutions/new");
  };

  const handleNlAnalyze = async (text: string) => {
    if (!token) {
      toast.error("로그인이 필요합니다.");
      return;
    }
    setNlLoading(true);
    setNlText(text);
    try {
      const result = await presets.analyzeText(token, text);
      setNlResult(result);
    } catch (e) {
      const message = e instanceof Error ? e.message : "분석에 실패했습니다.";
      toast.error(message);
      setNlResult(null);
    } finally {
      setNlLoading(false);
    }
  };

  const handleNlProceed = () => {
    if (!nlResult) return;
    // 분석 결과 + 원본 입력 텍스트를 sessionStorage에 저장 → 위저드 Step 1에서 prefill
    try {
      sessionStorage.setItem(
        NL_ANALYSIS_STORAGE_KEY,
        JSON.stringify({ ...nlResult, sourceText: nlText }),
      );
    } catch {
      // sessionStorage 사용 불가 시 무시 (SSR/프라이버시 모드)
    }
    router.push("/solutions/new");
  };

  const handleSkip = () => {
    router.push("/solutions/new");
  };

  return (
    <div className="mx-auto max-w-3xl">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Zap className="h-5 w-5 text-zinc-700" />
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">빠른 시작</h1>
        </div>
        <p className="text-sm text-[var(--text-muted)]">
          프리셋을 선택하면 에이전트, 스킬, 파이프라인이 자동으로 설정됩니다
        </p>
      </div>

      {/* 자연어 입력 */}
      <div className="mb-8 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
        <NaturalLanguageInput
          onAnalyze={handleNlAnalyze}
          onProceed={handleNlProceed}
          isLoading={nlLoading}
          result={nlResult}
        />
      </div>

      {/* 프리셋 카드 목록 */}
      <div className="mb-8">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-zinc-700" />
          <h2 className="text-sm font-medium text-[var(--text-primary)]">프리셋 선택</h2>
          <span className="text-xs text-[var(--text-muted)]">
            ({presetList.length}개)
          </span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-700" />
            <span className="ml-2 text-sm text-[var(--text-muted)]">
              프리셋 불러오는 중...
            </span>
          </div>
        ) : presetList.length === 0 ? (
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 py-12 text-center">
            <p className="text-sm text-[var(--text-muted)]">
              등록된 프리셋이 없습니다. 위저드에서 직접 설정하세요.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {presetList.map((preset) => (
              <PresetCard
                key={preset.id}
                preset={preset}
                selected={selectedPreset?.id === preset.id}
                onSelect={handleSelectPreset}
              />
            ))}
          </div>
        )}
      </div>

      {/* 하단 액션 버튼 */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={handleSkip}
          className="text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text-secondary)]"
        >
          건너뛰고 직접 설정하기
        </button>

        <button
          type="button"
          onClick={handleApplyAndStart}
          disabled={!selectedPreset}
          className={cn(
            "group flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
            !selectedPreset
              ? "cursor-not-allowed bg-zinc-100 text-[var(--text-muted)]"
              : "bg-zinc-900 text-white hover:bg-zinc-800",
          )}
        >
          프리셋 적용 후 시작
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </div>
  );
}
