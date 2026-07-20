"use client";

import { Coins } from "lucide-react";

export function CostCard() {
  return (
    <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-[0_1px_2px_rgba(20,24,33,0.05)]">
      <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-4 py-3.5">
        <h2 className="text-[13.5px] font-bold tracking-tight text-[var(--text-primary)]">
          AI 실행 비용
        </h2>
        <span className="ml-auto rounded-full bg-[var(--bg-hover)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
          MVP-2 예정
        </span>
      </div>

      <div className="flex flex-col gap-4 p-4">
        {/* 준비 중 빈 상태 */}
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[var(--border-subtle)] px-4 py-5 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--bg-hover)]">
            <Coins className="h-5 w-5 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-xs font-medium text-[var(--text-secondary)]">
            MVP-2에서 LLM 원장 연결 예정
          </p>
        </div>

        {/* 데이터 자리 표시 (비데이터 · 흐림) */}
        <div className="flex select-none flex-col gap-3 opacity-50" aria-hidden="true">
          <div className="flex flex-col gap-1.5">
            <div className="h-2.5 w-24 rounded bg-[var(--bg-hover)]" />
            <div className="h-6 w-32 rounded bg-[var(--bg-hover)]" />
          </div>
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-2.5">
              <div className="h-2 w-2 rounded-sm bg-[var(--accent)]" />
              <div className="h-2.5 w-20 rounded bg-[var(--bg-hover)]" />
              <div className="ml-auto h-1.5 flex-1 rounded bg-[var(--bg-hover)]" />
            </div>
            <div className="flex items-center gap-2.5">
              <div className="h-2 w-2 rounded-sm bg-[var(--text-muted)]" />
              <div className="h-2.5 w-16 rounded bg-[var(--bg-hover)]" />
              <div className="ml-auto h-1.5 flex-1 rounded bg-[var(--bg-hover)]" />
            </div>
          </div>
        </div>

        <p className="border-t border-[var(--border-subtle)] pt-3 text-[11.5px] leading-relaxed text-[var(--text-muted)]">
          사내 개발은 구독 세션을 우선 사용합니다. 대표 지표는{" "}
          <b className="font-semibold text-[var(--text-secondary)]">토큰</b>이며,
          금액은 조직 API 키 사용분에만 산정됩니다.
        </p>

        <div className="flex items-center justify-between text-[11.5px] text-[var(--text-muted)]">
          <span>이슈별 비용 분해</span>
          <span className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wide">
            2차 제공
          </span>
        </div>
      </div>
    </section>
  );
}
