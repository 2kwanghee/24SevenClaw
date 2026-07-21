"use client";

import { AlertTriangle, ExternalLink, Info } from "lucide-react";
import { useTranslations } from "next-intl";

import type {
  CustomerContractOverrideResponse,
  GovernancePolicyResponse,
} from "@/lib/api-client";

interface GovernancePolicyPanelProps {
  policy?: GovernancePolicyResponse | null;
  isLoading?: boolean;
  isError?: boolean;
  /** project별 적용된 계약 오버라이드 (선택) */
  overrides?: CustomerContractOverrideResponse[];
}

const TEMPORAL_URL = process.env.NEXT_PUBLIC_TEMPORAL_URL;

function PanelShell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-[0_1px_2px_rgba(20,24,33,0.05)]">
      <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-4 py-3.5">
        <h2 className="text-[13.5px] font-bold tracking-tight text-[var(--text-primary)]">
          {title}
        </h2>
      </div>
      {children}
    </section>
  );
}

function ToggleBadge({ on, label }: { on: boolean; label: string }) {
  return (
    <span
      className={`ml-auto inline-flex items-center gap-1.5 text-[11.5px] font-semibold ${
        on
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-[var(--text-muted)]"
      }`}
    >
      <span
        className={`relative h-[17px] w-[30px] rounded-full ${
          on ? "bg-emerald-500" : "bg-[var(--border-strong,#9ca3af)]"
        }`}
        aria-hidden="true"
      >
        <span
          className={`absolute top-0.5 h-[13px] w-[13px] rounded-full bg-white ${
            on ? "right-0.5" : "left-0.5"
          }`}
        />
      </span>
      {label}
    </span>
  );
}

export function GovernancePolicyPanel({
  policy,
  isLoading = false,
  isError = false,
  overrides,
}: GovernancePolicyPanelProps) {
  const t = useTranslations("governance");

  // 로딩
  if (isLoading) {
    return (
      <PanelShell title={t("title")}>
        <div className="flex flex-col gap-3 p-4" role="status" aria-label={t("loading")}>
          <div className="h-5 animate-pulse rounded bg-[var(--bg-hover)]" />
          <div className="h-5 w-2/3 animate-pulse rounded bg-[var(--bg-hover)]" />
          <div className="h-5 w-1/2 animate-pulse rounded bg-[var(--bg-hover)]" />
        </div>
      </PanelShell>
    );
  }

  // 에러 / 데이터 없음
  if (isError || !policy) {
    return (
      <PanelShell title={t("title")}>
        <div className="flex items-center gap-2 p-4 text-[12.5px] text-[var(--text-muted)]">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" aria-hidden="true" />
          {isError ? t("error") : t("empty")}
        </div>
      </PanelShell>
    );
  }

  const toggleEntries = Object.entries(policy.toggles ?? {});
  const activeOverrides = (overrides ?? []).filter((o) => o.is_active);

  return (
    <PanelShell title={t("title")}>
      <div className="flex flex-col gap-3.5 p-4">
        {/* 마스터 토글 */}
        <div className="flex items-center gap-2.5 text-[12.5px]">
          <span className="font-mono text-[var(--text-secondary)]">FLOWOPS_GOVERNANCE</span>
          <ToggleBadge
            on={policy.governance_enabled}
            label={policy.governance_enabled ? t("on") : t("off")}
          />
        </div>

        {!policy.governance_enabled && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11.5px] text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {t("disabled")}
          </div>
        )}

        <div className="h-px bg-[var(--border-subtle)]" />

        {/* 게이트 룰 */}
        <div>
          <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            {t("gateRules")}
          </p>
          <div className="flex flex-col gap-2">
            {policy.gate_rules.map((rule) => (
              <div key={rule.key} className="flex items-center gap-2.5 text-[12.5px]">
                <span
                  className={`font-mono ${
                    rule.enabled
                      ? "text-[var(--text-secondary)]"
                      : "text-[var(--text-muted)] line-through"
                  }`}
                >
                  {rule.key}
                </span>
                {!rule.enabled && (
                  <span className="text-[10px] text-[var(--text-muted)]">
                    {t("ruleDisabled")}
                  </span>
                )}
                <span
                  className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-bold ${
                    rule.mode === "block"
                      ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300"
                      : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                  }`}
                >
                  {rule.mode === "block" ? t("modeBlock") : t("modeWarn")}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="h-px bg-[var(--border-subtle)]" />

        {/* HIGH 위험 경로 */}
        <div>
          <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            {t("highRisk")}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {[...policy.high_risk.prefixes, ...policy.high_risk.patterns].map((path) => (
              <span
                key={path}
                className="rounded-md bg-amber-50 px-2 py-1 font-mono text-[11px] text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
              >
                {path}
              </span>
            ))}
          </div>
          {policy.risk_demote_to_pr && (
            <p className="mt-2 text-[11px] text-[var(--text-muted)]">{t("riskDemote")}</p>
          )}
        </div>

        {/* 토글 목록 */}
        {toggleEntries.length > 0 && (
          <>
            <div className="h-px bg-[var(--border-subtle)]" />
            <div>
              <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                {t("toggles")}
              </p>
              <div className="flex flex-col gap-1.5">
                {toggleEntries.map(([name, value]) => (
                  <div key={name} className="flex items-center gap-2.5 text-[11.5px]">
                    <span className="font-mono text-[var(--text-secondary)]">{name}</span>
                    <span
                      className={`ml-auto rounded px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wide ${
                        value
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                          : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
                      }`}
                    >
                      {value ? t("on") : t("off")}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* 적용된 계약 오버라이드 (선택) */}
        {overrides !== undefined && (
          <>
            <div className="h-px bg-[var(--border-subtle)]" />
            <div>
              <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                {t("overrides")}
              </p>
              {activeOverrides.length === 0 ? (
                <p className="text-[11.5px] text-[var(--text-muted)]">{t("overridesEmpty")}</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {activeOverrides.map((o) => (
                    <div key={o.id} className="flex items-center gap-2.5 text-[11.5px]">
                      <span className="truncate font-mono text-[var(--text-secondary)]">
                        {o.central_contract_id.slice(0, 8)}
                      </span>
                      <span className="ml-auto rounded bg-emerald-50 px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wide text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                        {t("overrideActive")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        <div className="h-px bg-[var(--border-subtle)]" />

        {/* 정책 출처 주의 라벨 */}
        {policy.source_note && (
          <div className="flex items-start gap-2 text-[11px] text-[var(--text-muted)]">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>
              <span className="font-semibold">{t("sourceNote")}:</span> {policy.source_note}
            </span>
          </div>
        )}

        {/* Temporal 링크 — env 미설정 시 숨김 */}
        {TEMPORAL_URL && (
          <a
            href={TEMPORAL_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--accent)] hover:underline"
          >
            {t("temporalLink")}
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        )}
      </div>
    </PanelShell>
  );
}
