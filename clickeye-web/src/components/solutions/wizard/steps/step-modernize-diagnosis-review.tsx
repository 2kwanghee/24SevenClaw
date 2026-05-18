"use client";

import { AlertTriangle, ChevronDown, Loader2, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSession } from "next-auth/react";

import {
  modernize,
  type CodebaseAnalysisResponse,
  type ModernizeRecommendationResponse,
} from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { cn } from "@/lib/utils";
import type { ModernizeScenario } from "@/types/solution-wizard";

/**
 * Step 3 (Modernize) — 진단 결과 + 시나리오 선택 + 권장안 검토.
 *
 * 마운트 시 GET /modernize/sessions/{id}/analysis + listRecommendations 동시 호출.
 * 사용자가 시나리오 라디오 선택 + 권장 카드 체크 → store 에 acceptedRecommendationIds 반영.
 * PATCH 로 selected=false 토글 시 백엔드 반영.
 */

const SCENARIO_LABELS: Record<ModernizeScenario, { title: string; desc: string }> = {
  versionup: {
    title: "VersionUp",
    desc: "패키지 버전 업그레이드 + EOL 런타임 대응",
  },
  refactor: {
    title: "Refactor",
    desc: "코드 스멜 / 레이어링 / 데드코드 정리",
  },
  language_migrate: {
    title: "LanguageMigrate",
    desc: "스택 전환 (예: Express → FastAPI)",
  },
};

export function StepModernizeDiagnosisReview() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const sessionId = useSolutionWizardStore((s) => s.modernize.sessionId);
  const scenario = useSolutionWizardStore((s) => s.modernize.scenario);
  const acceptedIds = useSolutionWizardStore(
    (s) => s.modernize.acceptedRecommendationIds,
  );
  const setModernize = useSolutionWizardStore((s) => s.setModernize);

  const [analysis, setAnalysis] = useState<CodebaseAnalysisResponse | null>(null);
  const [recs, setRecs] = useState<ModernizeRecommendationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!token || !sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const [analysisRes, recsRes] = await Promise.all([
        modernize.getAnalysis(token, sessionId),
        modernize.listRecommendations(token, sessionId),
      ]);
      setAnalysis(analysisRes);
      setRecs(recsRes);
      // selected=true 권장안 ID 를 store 에 반영 (사용자 토글 전 default)
      const selectedIds = recsRes.filter((r) => r.selected).map((r) => r.id);
      setModernize({ acceptedRecommendationIds: selectedIds });
    } catch (e) {
      setError(e instanceof Error ? e.message : "분석 결과 로딩 실패");
    } finally {
      setLoading(false);
    }
  }, [token, sessionId, setModernize]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const handleToggleRec = async (rec: ModernizeRecommendationResponse) => {
    if (!token || !sessionId) return;
    const newSelected = !rec.selected;
    // optimistic update
    setRecs((prev) =>
      prev.map((r) => (r.id === rec.id ? { ...r, selected: newSelected } : r)),
    );
    const newAccepted = newSelected
      ? [...acceptedIds, rec.id]
      : acceptedIds.filter((id) => id !== rec.id);
    setModernize({ acceptedRecommendationIds: newAccepted });
    try {
      await modernize.updateRecommendation(token, sessionId, rec.id, {
        selected: newSelected,
      });
    } catch {
      // 실패 시 rollback
      setRecs((prev) =>
        prev.map((r) => (r.id === rec.id ? { ...r, selected: rec.selected } : r)),
      );
    }
  };

  const handleScenarioChange = (s: ModernizeScenario) => {
    setModernize({ scenario: s });
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-zinc-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        진단 결과 로딩 중...
      </div>
    );
  }

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-600">
        {error}
      </p>
    );
  }

  const acceptedCount = recs.filter((r) => r.selected).length;

  return (
    <div className="space-y-5" role="region" aria-label="진단 검토">
      {/* 감지 스택 */}
      {analysis && (
        <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
          <h3 className="mb-3 text-sm font-medium text-zinc-700">감지된 스택</h3>
          <div className="space-y-2">
            {Object.keys(analysis.lang_distribution).length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(analysis.lang_distribution).map(([lang, ratio]) => (
                  <span
                    key={lang}
                    className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs text-zinc-700"
                  >
                    {lang} {(ratio * 100).toFixed(0)}%
                  </span>
                ))}
              </div>
            )}
            {Object.keys(analysis.framework_signals).length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(analysis.framework_signals).map(([fw, ver]) => (
                  <span
                    key={fw}
                    className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-700"
                  >
                    <code className="font-mono">{fw}</code>: {String(ver)}
                  </span>
                ))}
              </div>
            )}
            {analysis.risk_flags.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                {analysis.risk_flags.map((flag) => (
                  <span
                    key={flag}
                    className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-medium text-red-700"
                  >
                    {flag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* LLM summary (접이식) */}
      {analysis?.llm_summary_md && (
        <div className="rounded-xl border border-zinc-200">
          <button
            type="button"
            onClick={() => setSummaryExpanded((v) => !v)}
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-zinc-900"
            aria-expanded={summaryExpanded}
          >
            <span className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-zinc-500" />
              AI 진단 요약
            </span>
            <ChevronDown
              className={cn(
                "h-4 w-4 text-zinc-500 transition-transform",
                summaryExpanded && "rotate-180",
              )}
            />
          </button>
          {summaryExpanded && (
            <div className="border-t border-zinc-200 px-4 py-3 text-sm leading-relaxed text-zinc-700">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {analysis.llm_summary_md}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}

      {/* 시나리오 선택 */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-zinc-700">현대화 시나리오</h3>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {(Object.keys(SCENARIO_LABELS) as ModernizeScenario[]).map((s) => {
            const isSelected = scenario === s;
            return (
              <label
                key={s}
                className={cn(
                  "cursor-pointer rounded-xl border px-3 py-2.5 transition-colors",
                  isSelected
                    ? "border-zinc-900 bg-zinc-50 ring-2 ring-zinc-900/10"
                    : "border-zinc-200 hover:border-zinc-300",
                )}
              >
                <input
                  type="radio"
                  name="modernize-scenario"
                  value={s}
                  checked={isSelected}
                  onChange={() => handleScenarioChange(s)}
                  className="sr-only"
                />
                <p className="text-sm font-medium text-zinc-900">
                  {SCENARIO_LABELS[s].title}
                </p>
                <p className="mt-0.5 text-[11px] text-zinc-500">
                  {SCENARIO_LABELS[s].desc}
                </p>
              </label>
            );
          })}
        </div>
      </div>

      {/* 권장 카드 체크리스트 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-zinc-700">
            권장사항{" "}
            <span className="ml-1 text-[11px] font-normal text-zinc-500">
              ({acceptedCount}/{recs.length} 선택됨)
            </span>
          </h3>
        </div>
        {recs.length === 0 && (
          <p className="text-sm text-zinc-500">
            권장사항이 없습니다. 시나리오를 변경하거나 다시 분석해보세요.
          </p>
        )}
        <ul className="space-y-2">
          {recs.map((rec) => (
            <li
              key={rec.id}
              className={cn(
                "rounded-xl border px-4 py-3 transition-colors",
                rec.selected
                  ? "border-zinc-900 bg-white"
                  : "border-zinc-200 bg-zinc-50 opacity-70",
              )}
            >
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={rec.selected}
                  onChange={() => void handleToggleRec(rec)}
                  className="mt-1 h-4 w-4 shrink-0 cursor-pointer rounded border-zinc-300 accent-zinc-900"
                  aria-label={`${rec.title} 선택`}
                />
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center gap-1.5">
                    <span className="text-sm font-semibold text-zinc-900">
                      {rec.title}
                    </span>
                    <RiskBadge risk={rec.risk} />
                    <EffortBadge effort={rec.effort} />
                  </div>
                  {rec.rationale_md && (
                    <p className="text-xs text-zinc-600">
                      {rec.rationale_md.slice(0, 200)}
                      {rec.rationale_md.length > 200 ? "…" : ""}
                    </p>
                  )}
                  {rec.target_path && (
                    <p className="mt-1 font-mono text-[10px] text-zinc-400">
                      {rec.target_path}
                    </p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function RiskBadge({ risk }: { risk: "low" | "med" | "high" }) {
  const palette = {
    high: "bg-red-50 text-red-700",
    med: "bg-amber-50 text-amber-700",
    low: "bg-emerald-50 text-emerald-700",
  } as const;
  return (
    <span
      className={cn(
        "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
        palette[risk],
      )}
    >
      {risk}
    </span>
  );
}

function EffortBadge({ effort }: { effort: "S" | "M" | "L" }) {
  return (
    <span className="rounded-full bg-zinc-100 px-1.5 py-0.5 text-[10px] font-medium text-zinc-700">
      effort: {effort}
    </span>
  );
}
