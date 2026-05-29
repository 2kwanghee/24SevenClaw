"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { Loader2, RefreshCw, TrendingDown, Zap, Users, Clock } from "lucide-react";
import { useTranslations } from "next-intl";

import { roi, type RoiCalculateResponse } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { type RoiOverrides } from "@/types/solution-wizard";

function formatKRW(value: number): string {
  return new Intl.NumberFormat("ko-KR", { style: "currency", currency: "KRW", maximumFractionDigits: 0 }).format(value);
}

function formatDays(days: number, unit: string): string {
  return `${days.toFixed(1)}${unit}`;
}

export function StepSolutionRoi() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const t = useTranslations("wizard.step6.roi");

  const roleLabels: Record<string, string> = {
    pm: t("rolePm"),
    be: t("roleBe"),
    fe: t("roleFe"),
    qa: t("roleQa"),
    designer: t("roleDesigner"),
  };

  const { data: wizardData, setRoi } = useSolutionWizardStore();
  const { agents, platform, roi: roiState } = wizardData;

  const selectedProto = wizardData.prototypes.generatedPrototypes.find(
    (p) => p.id === wizardData.prototypes.selectedPrototypeId,
  );

  const solutionType = (selectedProto as { solution_type?: string } | undefined)?.solution_type ?? "custom";
  const complexity: "low" | "medium" | "high" =
    ((selectedProto as { complexity?: string } | undefined)?.complexity as "low" | "medium" | "high") ?? "medium";

  const [result, setResult] = useState<RoiCalculateResponse | null>(
    roiState.result
      ? {
          baseline_cost: roiState.result.baselineCost,
          clickeye_cost: roiState.result.clickeyeCost,
          savings: roiState.result.savings,
          savings_ratio: roiState.result.savingsRatio,
          baseline_days: roiState.result.baselineDays,
          clickeye_days: roiState.result.clickeyeDays,
          breakdown: roiState.result.breakdown,
          rates_snapshot: roiState.result.ratesSnapshot,
          formula_version: roiState.result.formulaVersion,
        }
      : null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 직군별 단가 오버라이드 (표준값 표시 + 현장 조정)
  const [overrideRates, setOverrideRates] = useState<Record<string, string>>(() => {
    const saved = roiState.overrides.roleRates ?? {};
    return Object.fromEntries(Object.entries(saved).map(([k, v]) => [k, String(v)]));
  });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const buildOverrides = useCallback(
    (rates: Record<string, string>): Record<string, number> => {
      const out: Record<string, number> = {};
      for (const [k, v] of Object.entries(rates)) {
        const n = parseFloat(v);
        if (!isNaN(n) && n > 0) out[`role_rate.${k}`] = n;
      }
      return out;
    },
    [],
  );

  const calculate = useCallback(
    async (rates: Record<string, string>) => {
      if (!token) return;
      setLoading(true);
      setError(null);
      try {
        const res = await roi.calculate(token, {
          solution_type: solutionType,
          complexity,
          selected_agents_count: agents.selectedAgents.length,
          selected_skills_count: agents.selectedSkills.length,
          selected_hooks_count: agents.selectedHooks.length,
          platform_id: platform.platformId ?? undefined,
          overrides: Object.keys(buildOverrides(rates)).length > 0 ? buildOverrides(rates) : undefined,
        });
        setResult(res);
        // 스토어 커밋 (wizard_data에 스냅샷 저장)
        const ovr: RoiOverrides = {
          roleRates: buildOverrides(rates) as Record<string, number>,
        };
        setRoi({
          overrides: ovr,
          result: {
            baselineCost: res.baseline_cost,
            clickeyeCost: res.clickeye_cost,
            savings: res.savings,
            savingsRatio: res.savings_ratio,
            baselineDays: res.baseline_days,
            clickeyeDays: res.clickeye_days,
            breakdown: res.breakdown,
            ratesSnapshot: res.rates_snapshot,
            formulaVersion: res.formula_version,
          },
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : t("calcFailed"));
      } finally {
        setLoading(false);
      }
    },
    [token, solutionType, complexity, agents, platform, buildOverrides, setRoi],
  );

  // 마운트 시 계산 (저장된 결과가 없을 때)
  useEffect(() => {
    if (!result) {
      void calculate(overrideRates);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleRateChange(roleKey: string, value: string) {
    const next = { ...overrideRates, [roleKey]: value };
    setOverrideRates(next);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => void calculate(next), 400);
  }

  function handleReset() {
    setOverrideRates({});
    void calculate({});
  }

  const savingsPercent = result ? Math.round(result.savings_ratio * 100) : 0;
  const standardRates = result?.rates_snapshot?.["role_rate"] ?? {};

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">{t("title")}</h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          {t("desc")}
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button onClick={() => void calculate(overrideRates)} className="ml-auto shrink-0">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {loading && !result && (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
        </div>
      )}

      {result && (
        <>
          {/* 비교 카드 */}
          <div className="grid grid-cols-2 gap-4">
            {/* 기존 인력 비용 */}
            <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 shadow-sm">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-500">
                <Users className="h-4 w-4" />
                {t("baselineCard")}
              </div>
              <p className="text-2xl font-bold text-[var(--text-primary)]">
                {loading ? <Loader2 className="inline h-5 w-5 animate-spin" /> : formatKRW(result.baseline_cost)}
              </p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                <Clock className="mr-1 inline h-3.5 w-3.5" />
                {formatDays(result.baseline_days, t("daysUnit"))} {t("timeSuffix")}
              </p>
            </div>

            {/* ClickEye 비용 */}
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-emerald-700">
                <Zap className="h-4 w-4" />
                {t("clickeyeCard")}
              </div>
              <p className="text-2xl font-bold text-emerald-700">
                {loading ? <Loader2 className="inline h-5 w-5 animate-spin" /> : formatKRW(result.clickeye_cost)}
              </p>
              <p className="mt-1 text-xs text-emerald-600">
                <Clock className="mr-1 inline h-3.5 w-3.5" />
                {formatDays(result.clickeye_days, t("daysUnit"))} {t("timeSuffix")}
              </p>
            </div>
          </div>

          {/* 절감 강조 */}
          <div className="rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 p-5">
            <div className="flex items-center gap-3">
              <TrendingDown className="h-5 w-5 text-emerald-600" />
              <div>
                <p className="text-xs text-emerald-600">{t("savingsLabel")}</p>
                <p className="text-xl font-bold text-emerald-700">
                  {loading ? "..." : formatKRW(result.savings)}
                </p>
              </div>
              <div className="ml-auto text-right">
                <p className="text-xs text-emerald-600">{t("savingsRateLabel")}</p>
                <p className="text-3xl font-bold text-emerald-700">{savingsPercent}%</p>
              </div>
            </div>

            {/* 가로 막대 */}
            <div className="mt-4 space-y-2">
              <div>
                <div className="mb-1 flex justify-between text-xs text-[var(--text-muted)]">
                  <span>{t("traditionalLabel")}</span>
                  <span>100%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-zinc-200">
                  <div className="h-2 rounded-full bg-zinc-400" style={{ width: "100%" }} />
                </div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs text-emerald-600">
                  <span>ClickEye</span>
                  <span>{Math.round((1 - result.savings_ratio) * 100)}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-emerald-100">
                  <div
                    className="h-2 rounded-full bg-emerald-500 transition-all duration-500"
                    style={{ width: `${Math.max(3, Math.round((1 - result.savings_ratio) * 100))}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* 직군별 공수 명세 + 단가 오버라이드 */}
          <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">{t("breakdownTitle")}</h3>
              {Object.keys(overrideRates).length > 0 && (
                <button
                  onClick={handleReset}
                  className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] underline"
                >
                  {t("resetBtn")}
                </button>
              )}
            </div>

            <div className="space-y-3">
              {result.breakdown.map((item) => {
                const stdRate = standardRates[item.role_key];
                const overrideVal = overrideRates[item.role_key] ?? "";
                const isOverridden = overrideVal && parseFloat(overrideVal) !== stdRate;

                return (
                  <div key={item.role_key} className="flex items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-[var(--text-primary)]">
                          {roleLabels[item.role_key] ?? item.label}
                        </span>
                        <span className="text-sm font-medium text-[var(--text-primary)]">
                          {loading ? "..." : formatKRW(item.subtotal)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                        <span>{formatDays(item.days, t("daysUnit"))}</span>
                        <span>×</span>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            value={overrideVal || String(item.rate)}
                            onChange={(e) => handleRateChange(item.role_key, e.target.value)}
                            className={`w-28 rounded border px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-zinc-300 ${
                              isOverridden
                                ? "border-amber-300 bg-amber-50 text-amber-700"
                                : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-muted)]"
                            }`}
                          />
                          <span>{t("perDay")}</span>
                          {isOverridden && (
                            <span className="rounded bg-amber-100 px-1 py-0.5 text-[10px] text-amber-600">{t("adjustedBadge")}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <p className="mt-4 text-[10px] text-[var(--text-muted)]">
              {t("rateNote", { version: result.formula_version })}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
