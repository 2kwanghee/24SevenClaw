"use client";

import { ExternalLink } from "lucide-react";

const GATE_RULES: { key: string; label: string; mode: "block" | "warn" }[] = [
  { key: "contract-drift", label: "차단", mode: "block" },
  { key: "ticket-ref", label: "차단", mode: "block" },
  { key: "plan-trace", label: "권고", mode: "warn" },
];

const HIGH_RISK_PATHS = [
  "clickeye-contracts/**",
  "clickeye-infra/**",
  "*auth*",
  "보안",
];

export function GovernancePolicyPanel() {
  return (
    <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-[0_1px_2px_rgba(20,24,33,0.05)]">
      <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-4 py-3.5">
        <h2 className="text-[13.5px] font-bold tracking-tight text-[var(--text-primary)]">
          거버넌스 정책
        </h2>
      </div>

      <div className="flex flex-col gap-3.5 p-4">
        {/* 마스터 토글 */}
        <div className="flex items-center gap-2.5 text-[12.5px]">
          <span className="text-[var(--text-secondary)]">FLOWOPS_GOVERNANCE</span>
          <span className="ml-auto inline-flex items-center gap-1.5 text-[11.5px] font-semibold text-emerald-600 dark:text-emerald-400">
            <span
              className="relative h-[17px] w-[30px] rounded-full bg-emerald-500"
              aria-hidden="true"
            >
              <span className="absolute right-0.5 top-0.5 h-[13px] w-[13px] rounded-full bg-white" />
            </span>
            ON
          </span>
        </div>

        <div className="h-px bg-[var(--border-subtle)]" />

        {/* 게이트 룰 */}
        {GATE_RULES.map((rule) => (
          <div key={rule.key} className="flex items-center gap-2.5 text-[12.5px]">
            <span className="font-mono text-[var(--text-secondary)]">{rule.key}</span>
            <span
              className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-bold ${
                rule.mode === "block"
                  ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300"
                  : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
              }`}
            >
              {rule.label}
            </span>
          </div>
        ))}

        <div className="h-px bg-[var(--border-subtle)]" />

        {/* HIGH 위험 경로 */}
        <div>
          <p className="mb-2 text-[10.5px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            HIGH 위험 경로 · 직접머지 금지
          </p>
          <div className="flex flex-wrap gap-1.5">
            {HIGH_RISK_PATHS.map((path) => (
              <span
                key={path}
                className="rounded-md bg-amber-50 px-2 py-1 font-mono text-[11px] text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
              >
                {path}
              </span>
            ))}
          </div>
        </div>

        <div className="h-px bg-[var(--border-subtle)]" />

        {/* 2차 제공 + Temporal 링크 */}
        <div className="flex items-center justify-between text-[11.5px] text-[var(--text-muted)]">
          <span>게이트 결정 이력</span>
          <span className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wide">
            2차 제공
          </span>
        </div>
        <a
          href="http://localhost:8080"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-cyan-700 hover:underline dark:text-cyan-400"
        >
          Temporal UI (:8080) 열기
          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>
    </section>
  );
}
