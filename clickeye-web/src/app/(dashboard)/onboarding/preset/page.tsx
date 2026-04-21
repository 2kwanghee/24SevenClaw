"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles, ArrowRight, Zap } from "lucide-react";

import { cn } from "@/lib/utils";
import { usePresets } from "@/hooks/use-presets";
import { PresetCard } from "@/components/presets/preset-card";
import { NaturalLanguageInput } from "@/components/presets/natural-language-input";
import type { PresetResponse, NaturalLanguageConfigResponse } from "@/lib/api-client";

export default function PresetSelectionPage() {
  const router = useRouter();
  const { data, isLoading } = usePresets();
  const [selectedPreset, setSelectedPreset] = useState<PresetResponse | null>(null);
  const [nlResult, setNlResult] = useState<NaturalLanguageConfigResponse | null>(null);
  const [nlLoading, setNlLoading] = useState(false);

  const presetList = data?.items ?? [];

  const handleSelectPreset = (preset: PresetResponse) => {
    setSelectedPreset((prev) => (prev?.id === preset.id ? null : preset));
  };

  const handleApplyAndStart = () => {
    if (!selectedPreset) return;
    router.push("/solutions/new");
  };

  const handleNlAnalyze = (text: string) => {
    setNlLoading(true);
    // 자연어 분석은 현재 클라이언트 측 키워드 매칭으로 동작
    // 향후 API 엔드포인트 완성 시 교체 예정
    setTimeout(() => {
      const lower = text.toLowerCase();
      const agents: string[] = ["harness"];
      const skills: string[] = [];
      const pipelines: string[] = [];

      if (lower.includes("백엔드") || lower.includes("api") || lower.includes("fastapi")) {
        agents.push("backend");
      }
      if (lower.includes("프론트") || lower.includes("react") || lower.includes("next")) {
        agents.push("frontend");
      }
      if (lower.includes("풀스택") || lower.includes("fullstack")) {
        agents.push("fullstack");
      }
      if (lower.includes("ui") || lower.includes("디자인") || lower.includes("ux")) {
        agents.push("uiux");
      }
      if (lower.includes("devops") || lower.includes("배포") || lower.includes("docker")) {
        agents.push("devops");
      }
      if (lower.includes("리뷰") || lower.includes("review")) {
        skills.push("code-review");
        pipelines.push("ai-review");
      }
      if (lower.includes("테스트") || lower.includes("test")) {
        skills.push("testing-basic");
        pipelines.push("simple-build");
      }
      if (lower.includes("코드 생성") || lower.includes("generation")) {
        skills.push("code-generation");
      }

      setNlResult({
        suggested_agents: agents,
        suggested_skills: skills,
        suggested_pipelines: pipelines,
        confidence: 0.7 + Math.random() * 0.25,
        reasoning: `입력에서 ${agents.length - 1}개 에이전트, ${skills.length}개 스킬, ${pipelines.length}개 파이프라인을 추출했습니다. 프리셋을 선택하면 추가 최적화가 적용됩니다.`,
      });
      setNlLoading(false);
    }, 800);
  };

  const handleSkip = () => {
    router.push("/solutions/new");
  };

  return (
    <div className="mx-auto max-w-3xl">
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Zap className="h-5 w-5 text-violet-400" />
          <h1 className="text-2xl font-bold text-white">빠른 시작</h1>
        </div>
        <p className="text-sm text-slate-400">
          프리셋을 선택하면 에이전트, 스킬, 파이프라인이 자동으로 설정됩니다
        </p>
      </div>

      {/* 자연어 입력 */}
      <div className="mb-8 rounded-2xl border border-white/5 bg-white/[0.02] p-6">
        <NaturalLanguageInput
          onAnalyze={handleNlAnalyze}
          isLoading={nlLoading}
          result={nlResult}
        />
      </div>

      {/* 프리셋 카드 목록 */}
      <div className="mb-8">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-violet-400" />
          <h2 className="text-sm font-medium text-white">프리셋 선택</h2>
          <span className="text-xs text-slate-500">
            ({presetList.length}개)
          </span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-violet-400" />
            <span className="ml-2 text-sm text-slate-400">
              프리셋 불러오는 중...
            </span>
          </div>
        ) : presetList.length === 0 ? (
          <div className="rounded-xl border border-white/5 bg-white/[0.02] px-6 py-12 text-center">
            <p className="text-sm text-slate-500">
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
          className="text-sm text-slate-400 transition-colors hover:text-white"
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
              ? "cursor-not-allowed bg-violet-600/30 text-violet-300/50"
              : "bg-violet-600 text-white shadow-lg shadow-violet-600/25 hover:bg-violet-500",
          )}
        >
          프리셋 적용 후 시작
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
    </div>
  );
}
