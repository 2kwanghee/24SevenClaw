"use client";

import { useState } from "react";
import { Sparkles, Loader2, ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

interface NaturalLanguageInputProps {
  onAnalyze: (text: string) => void;
  onProceed?: () => void;
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
  onProceed,
  isLoading = false,
  result,
}: NaturalLanguageInputProps) {
  const [text, setText] = useState("");
  const t = useTranslations("onboarding.naturalLanguage");

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
            {t("title")}
          </span>
        </div>
        <p className="mb-3 text-xs text-[var(--text-muted)]">{t("subtitle")}</p>

        <textarea data-gramm="false" data-gramm_editor="false"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("placeholder")}
          rows={3}
          maxLength={2000}
          disabled={isLoading}
          aria-label={t("ariaLabel")}
          className={cn(
            "w-full resize-none rounded-xl border bg-[var(--bg-surface)] px-4 py-3 text-sm text-[var(--text-primary)]",
            "placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2",
            "transition-all duration-200",
            isLoading
              ? "border-[var(--border-subtle)] opacity-60"
              : "border-[var(--border-subtle)] focus:border-zinc-400 focus:ring-zinc-400/20",
          )}
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-[10px] text-[var(--text-muted)]">
            {text.length}/2000
          </span>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!text.trim() || isLoading}
            aria-label={t("analyzeAriaLabel")}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-medium transition-all",
              !text.trim() || isLoading
                ? "cursor-not-allowed bg-[var(--bg-hover)] text-[var(--text-muted)]"
                : "bg-zinc-900 text-white hover:bg-zinc-800",
            )}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                {t("analyzing")}
              </>
            ) : (
              <>
                {t("analyzeBtn")}
                <ArrowRight className="h-3 w-3" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* 분석 결과 */}
      {result && (
        <div className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-medium text-violet-700">
            <Sparkles className="h-3 w-3" />
            {t("resultTitle")}
            <span className="ml-auto text-[10px] text-[var(--text-muted)]">
              {t("confidence", { percent: Math.round(result.confidence * 100) })}
            </span>
          </p>
          <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
            {result.reasoning}
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {result.suggested_agents.length > 0 && (
              <span className="rounded-md bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
                {t("agentsCount", { count: result.suggested_agents.length })}
              </span>
            )}
            {result.suggested_skills.length > 0 && (
              <span className="rounded-md bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
                {t("skillsCount", { count: result.suggested_skills.length })}
              </span>
            )}
            {result.suggested_pipelines.length > 0 && (
              <span className="rounded-md bg-[var(--bg-hover)] px-2 py-0.5 text-[11px] text-[var(--text-secondary)]">
                {t("pipelinesCount", { count: result.suggested_pipelines.length })}
              </span>
            )}
          </div>
          {onProceed && (
            <div className="pt-2">
              <button
                type="button"
                onClick={onProceed}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-violet-500"
              >
                {t("proceedBtn")}
                <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
