"use client";

import { useState } from "react";
import { Sparkles, Loader2, ArrowRight } from "lucide-react";

import { cn } from "@/lib/utils";

interface NaturalLanguageInputProps {
  onAnalyze: (text: string) => void;
  isLoading?: boolean;
  result?: {
    suggested_agents: string[];
    suggested_skills: string[];
    suggested_pipelines: string[];
    confidence: number;
    reasoning: string;
  } | null;
}

export function NaturalLanguageInput({
  onAnalyze,
  isLoading = false,
  result,
}: NaturalLanguageInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onAnalyze(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="space-y-4">
      <div className="relative">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-4 w-4 text-violet-600" />
          <span className="text-sm font-medium text-[var(--text-primary)]">
            자연어로 설정하기
          </span>
        </div>
        <p className="mb-3 text-xs text-[var(--text-muted)]">
          원하는 프로젝트를 자연어로 설명하면 최적의 설정을 추천합니다
        </p>

        <div className="relative">
          <textarea data-gramm="false" data-gramm_editor="false"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="예: Next.js + FastAPI로 SaaS를 만들고 싶어요. 코드 리뷰와 테스트 자동화가 필요합니다."
            rows={3}
            maxLength={2000}
            disabled={isLoading}
            aria-label="자연어 설정 입력"
            className={cn(
              "w-full resize-none rounded-xl border bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-primary)]",
              "placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2",
              "transition-all duration-200",
              isLoading
                ? "border-[var(--border-subtle)] opacity-60"
                : "border-[var(--border-subtle)] focus:border-zinc-400 focus:ring-zinc-400/20",
            )}
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!text.trim() || isLoading}
            aria-label="설정 분석하기"
            className={cn(
              "absolute bottom-3 right-3 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
              !text.trim() || isLoading
                ? "cursor-not-allowed bg-[var(--bg-hover)] text-[var(--text-muted)]"
                : "bg-zinc-900 text-white hover:bg-zinc-800",
            )}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                분석 중...
              </>
            ) : (
              <>
                분석하기
                <ArrowRight className="h-3 w-3" />
              </>
            )}
          </button>
        </div>
        <div className="mt-1 text-right text-[10px] text-[var(--text-muted)]">
          {text.length}/2000
        </div>
      </div>

      {/* 분석 결과 */}
      {result && (
        <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-medium text-violet-700">
            <Sparkles className="h-3 w-3" />
            AI 분석 결과
            <span className="ml-auto text-[10px] text-[var(--text-muted)]">
              신뢰도 {Math.round(result.confidence * 100)}%
            </span>
          </p>
          <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
            {result.reasoning}
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {result.suggested_agents.length > 0 && (
              <span className="rounded-md bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
                에이전트 {result.suggested_agents.length}개
              </span>
            )}
            {result.suggested_skills.length > 0 && (
              <span className="rounded-md bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
                스킬 {result.suggested_skills.length}개
              </span>
            )}
            {result.suggested_pipelines.length > 0 && (
              <span className="rounded-md bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
                파이프라인 {result.suggested_pipelines.length}개
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
