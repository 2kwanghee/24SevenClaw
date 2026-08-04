"use client";

import { useTranslations } from "next-intl";

import type { PipelineRun, PipelineRunEvent } from "@/lib/api-client";

// 이벤트 톤 — 실패(qa exit!=0 / outcome failed)·경고(model_mismatch)는 즉시 눈에 띄게.
const DOT_COLORS = {
  positive: "bg-emerald-500",
  negative: "bg-red-500",
  warning: "bg-amber-500",
  neutral: "bg-[var(--border-medium)]",
} as const;

type Tone = keyof typeof DOT_COLORS;

function eventTone(event: PipelineRunEvent): Tone {
  if (event.event === "model_mismatch") return "warning";
  if (event.event === "qa_done") {
    const exit = event.data?.["exit"];
    if (typeof exit === "number" && exit !== 0) return "negative";
  }
  if (event.event === "run_done") {
    return event.data?.["outcome"] === "failed" ? "negative" : "positive";
  }
  if (event.event === "refine_done" || event.event === "impl_done") {
    return "positive";
  }
  return "neutral";
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

interface EventDataProps {
  data: Record<string, unknown>;
}

/**
 * data 는 이벤트별 임의 키를 가진다. 알려진 키는 현지화 라벨, 나머지는 key=value 로
 * 나열해 정보를 잃지 않는다.
 */
function EventData({ data }: EventDataProps) {
  const t = useTranslations("delivery.pipeline");
  const entries = Object.entries(data);
  if (entries.length === 0) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
      {entries.map(([k, v]) => {
        const label = t.has(`dataKey.${k}`) ? t(`dataKey.${k}`) : k;
        return (
          <span
            key={k}
            className="font-mono text-[11px] tabular-nums text-[var(--text-secondary)]"
          >
            <span className="text-[var(--text-muted)]">{label}</span>=
            {formatValue(v)}
          </span>
        );
      })}
    </div>
  );
}

interface PipelineRunThreadProps {
  run: PipelineRun;
}

/** 선택된 런의 이벤트 타임라인 — intake-chain 의 세로 레일 구조 이식(타입은 새로). */
export function PipelineRunThread({ run }: PipelineRunThreadProps) {
  const t = useTranslations("delivery.pipeline");

  if (run.events.length === 0) {
    return <p className="text-xs text-[var(--text-muted)]">{t("thread.empty")}</p>;
  }

  return (
    <ol className="space-y-0">
      {run.events.map((event, index) => {
        const tone = eventTone(event);
        const isLast = index === run.events.length - 1;
        const eventLabel = t.has(`eventName.${event.event}`)
          ? t(`eventName.${event.event}`)
          : event.event;
        const when = event.occurred_at ?? event.created_at;
        return (
          <li key={`${event.event}-${index}`} className="flex gap-3">
            {/* 좌측 레일: 점 + 연결선(마지막 항목은 선 없음) */}
            <div className="flex flex-col items-center pt-1.5">
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${DOT_COLORS[tone]}`}
                aria-hidden="true"
              />
              {!isLast && (
                <span className="mt-1 w-px flex-1 bg-[var(--border-subtle)]" />
              )}
            </div>
            <div className={`min-w-0 flex-1 ${isLast ? "" : "pb-3"}`}>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="text-xs font-medium text-[var(--text-primary)]">
                  {eventLabel}
                </span>
                <time className="text-xs tabular-nums text-[var(--text-muted)]">
                  {when ? new Date(when).toLocaleString("ko-KR") : "—"}
                </time>
              </div>
              <EventData data={event.data} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
