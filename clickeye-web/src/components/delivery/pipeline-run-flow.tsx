"use client";

import { Fragment } from "react";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Check,
  Code2,
  FlaskConical,
  Flag,
  Loader2,
  type LucideIcon,
  Minus,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import type {
  PipelineRun,
  PipelineRunEvent,
  PipelineRunUsage,
} from "@/lib/api-client";

// ---------------------------------------------------------------------------
// 이벤트 → 단계 매핑 (순수 로직 — 테스트 대상)
// ---------------------------------------------------------------------------

/** 화면에 노드로 그려지는 5단계. model_mismatch 는 단계가 아니라 경고 배지다. */
export const STAGE_KEYS = ["refine", "impl", "qa", "gate", "done"] as const;
export type StageKey = (typeof STAGE_KEYS)[number];

/** 각 단계의 완료를 표시하는 `*_done` 이벤트명. */
const STAGE_EVENT: Record<StageKey, string> = {
  refine: "refine_done",
  impl: "impl_done",
  qa: "qa_done",
  gate: "gate_done",
  done: "run_done",
};

/**
 * 노드 상태 5종.
 * - done: 해당 `*_done` 이벤트가 있고 실패 조건이 아님
 * - failed: qa_done.exit != 0, 또는 run_done.outcome === "failed"
 * - skipped: run_done 이 있는데(런 종료됨) 그 단계 이벤트만 없음 — 기록 없음/건너뜀.
 *   `gate_done` 은 거버넌스 활성 경로에서만 기록되므로 완료된 런에도 없을 수 있다.
 *   "실행 안 됨"이 아니라 "이벤트 없음"이다 — 실행 여부를 단정하지 않는다.
 * - inferred: run_done 이 없고, 그 단계 이벤트도 없으며 직전 단계가 done (추정 진행)
 * - pending: run_done 도 없고 그 앞 단계도 미완
 */
export type StageStatus =
  | "done"
  | "failed"
  | "skipped"
  | "inferred"
  | "pending";

export interface StageState {
  key: StageKey;
  status: StageStatus;
  /** 초 단위 소요시간. impl 은 실측(derived=false), 나머지는 이벤트 시각 차 유도. */
  durationS?: number;
  /** 소요시간이 연속 occurred_at 차이로 유도된 값인지(true=유도, ~ 표기). */
  durationDerived?: boolean;
}

function isQaFailed(ev: PipelineRunEvent): boolean {
  const exit = ev.data?.["exit"];
  return typeof exit === "number" && exit !== 0;
}

/** occurred_at 이 둘 다 있으면 초 단위 차이를 반환(음수/NaN 은 무시). */
function diffSeconds(a: string | null, b: string | null): number | undefined {
  if (!a || !b) return undefined;
  const ms = new Date(a).getTime() - new Date(b).getTime();
  if (Number.isNaN(ms) || ms < 0) return undefined;
  return Math.round(ms / 1000);
}

/**
 * 파이프라인 이벤트 배열을 5단계 노드 상태로 변환한다.
 * 시작 이벤트가 없어(`*_done` 만 존재) "진행 중"은 직전 완료 단계의 다음 단계로 추론한다.
 */
export function computePipelineStages(events: PipelineRunEvent[]): StageState[] {
  // 각 이벤트는 런당 1회이므로 첫 출현만 취한다.
  const byEvent = new Map<string, PipelineRunEvent>();
  for (const e of events) {
    if (!byEvent.has(e.event)) byEvent.set(e.event, e);
  }

  const hasRunDone = byEvent.has("run_done");
  const runOutcome = byEvent.get("run_done")?.data?.["outcome"];

  const stages: StageState[] = [];
  let inferredUsed = false;

  STAGE_KEYS.forEach((key, i) => {
    const ev = byEvent.get(STAGE_EVENT[key]);
    let status: StageStatus;

    if (ev) {
      if (key === "qa" && isQaFailed(ev)) status = "failed";
      else if (key === "done" && runOutcome === "failed") status = "failed";
      else status = "done";
    } else if (hasRunDone) {
      // 런이 종료됐는데 이 단계 이벤트만 없다 → 기록 없음(대기가 아니다).
      status = "skipped";
    } else {
      const prevDone = i > 0 && stages[i - 1]?.status === "done";
      if (prevDone && !inferredUsed) {
        status = "inferred";
        inferredUsed = true;
      } else {
        status = "pending";
      }
    }

    // 소요시간: impl 은 impl_done.data.duration_s 를 그대로(실측), 나머지는 유도.
    let durationS: number | undefined;
    let durationDerived: boolean | undefined;
    if (ev) {
      if (key === "impl" && typeof ev.data?.["duration_s"] === "number") {
        durationS = ev.data["duration_s"] as number;
        durationDerived = false;
      } else {
        const prevEv = i > 0 ? byEvent.get(STAGE_EVENT[STAGE_KEYS[i - 1]]) : undefined;
        const derived = diffSeconds(ev.occurred_at, prevEv?.occurred_at ?? null);
        if (derived !== undefined) {
          durationS = derived;
          durationDerived = true;
        }
      }
    }

    stages.push({ key, status, durationS, durationDerived });
  });

  return stages;
}

/** model_mismatch 이벤트 존재 여부 — 헤더 경고 배지용(단계 아님). */
export function hasModelMismatch(events: PipelineRunEvent[]): boolean {
  return events.some((e) => e.event === "model_mismatch");
}

/** run_done.outcome 6값 → 배지 색. 알 수 없는 값은 muted 로 폴백한다. */
export const OUTCOME_TONE: Record<string, string> = {
  pushed:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  merged:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300",
  pr: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300",
  demoted:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
  failed:
    "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300",
  unknown:
    "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
};

// ---------------------------------------------------------------------------
// 토큰 합산 (순수 로직 — 테스트 대상)
// ---------------------------------------------------------------------------

export interface PipelineUsageTotals {
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  /** 사용된 모델 이름(중복 제거, 최초 등장 순). */
  models: string[];
  /** 중복 제거 후 티켓 수. */
  ticketCount: number;
  /** 입력 런 수(중복 제거 전). */
  runCount: number;
}

/**
 * 프로젝트 단위 토큰 합산.
 *
 * usage 는 티켓(issue_key) 단위 집계라 같은 티켓의 여러 런에 동일 값이 실린다.
 * 런을 그대로 더하면 이중계상되므로 issue_key 로 중복 제거해 티켓당 1회만 더한다.
 */
export function aggregatePipelineUsage(
  runs: PipelineRun[],
): PipelineUsageTotals {
  const byTicket = new Map<string, PipelineRunUsage>();
  for (const r of runs) {
    if (!byTicket.has(r.issue_key)) byTicket.set(r.issue_key, r.usage);
  }
  let input_tokens = 0;
  let output_tokens = 0;
  let cache_read_tokens = 0;
  const models: string[] = [];
  for (const u of byTicket.values()) {
    input_tokens += u.input_tokens;
    output_tokens += u.output_tokens;
    cache_read_tokens += u.cache_read_tokens;
    for (const m of u.models) {
      if (!models.includes(m)) models.push(m);
    }
  }
  return {
    input_tokens,
    output_tokens,
    cache_read_tokens,
    models,
    ticketCount: byTicket.size,
    runCount: runs.length,
  };
}

function fmtTokens(value: number): string {
  return value.toLocaleString("en-US");
}

/**
 * 티켓 소비 토큰 바 — 입력·출력·캐시읽기 세 항목 모두 표시.
 * 캐시읽기가 실측에서 지배적(출력의 수백 배)이라 시각적으로 묻히지 않게 강조한다.
 */
export function PipelineUsageBar({ runs }: { runs: PipelineRun[] }) {
  const t = useTranslations("delivery.pipeline");
  const u = aggregatePipelineUsage(runs);
  return (
    <div className="flex flex-col gap-2.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
          {t("usage.title")}
        </span>
        <span className="text-[11px] text-[var(--text-muted)]">
          {t("usage.ticketCount", { count: u.ticketCount })}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] font-medium text-[var(--text-muted)]">
            {t("usage.input")}
          </span>
          <span className="font-mono text-sm tabular-nums text-[var(--text-secondary)]">
            {fmtTokens(u.input_tokens)}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] font-medium text-[var(--text-muted)]">
            {t("usage.output")}
          </span>
          <span className="font-mono text-sm tabular-nums text-[var(--text-secondary)]">
            {fmtTokens(u.output_tokens)}
          </span>
        </div>
        {/* 캐시읽기 — 지배적 소비원이라 accent + 큰 글자로 강조 */}
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] font-semibold text-[var(--accent)]">
            {t("usage.cacheRead")}
          </span>
          <span className="font-mono text-base font-bold tabular-nums text-[var(--accent)]">
            {fmtTokens(u.cache_read_tokens)}
          </span>
        </div>
      </div>
      {/* 사용 모델 — 원가 판단 근거 */}
      {u.models.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-medium text-[var(--text-muted)]">
            {t("usage.models")}
          </span>
          {u.models.map((m) => (
            <span
              key={m}
              className="rounded border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]"
            >
              {m}
            </span>
          ))}
        </div>
      )}
      <p className="text-[11px] leading-relaxed text-[var(--text-muted)]">
        {t("usage.dedupeNote")}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 렌더링
// ---------------------------------------------------------------------------

interface PipelineRunFlowProps {
  run: PipelineRun;
}

/** 단계별 고유 아이콘 — 노드의 정체성(상태와 무관). */
const STAGE_ICON: Record<StageKey, LucideIcon> = {
  refine: Sparkles,
  impl: Code2,
  qa: FlaskConical,
  gate: ShieldCheck,
  done: Flag,
};

/**
 * 단계 고유색 — 정상 흐름(done/inferred/pending)에서 노드를 구분한다.
 * 상태색(실패=red/기록없음=muted)은 아래 statusChrome 이 별도 채널로 덮어쓴다.
 */
const STAGE_TONE: Record<StageKey, { card: string; circle: string; icon: string }> = {
  refine: {
    card: "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/40",
    circle: "bg-blue-100 dark:bg-blue-900/50",
    icon: "text-blue-600 dark:text-blue-300",
  },
  impl: {
    card: "border-violet-200 bg-violet-50 dark:border-violet-800 dark:bg-violet-950/40",
    circle: "bg-violet-100 dark:bg-violet-900/50",
    icon: "text-violet-600 dark:text-violet-300",
  },
  qa: {
    card: "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/40",
    circle: "bg-amber-100 dark:bg-amber-900/50",
    icon: "text-amber-600 dark:text-amber-300",
  },
  gate: {
    card: "border-teal-200 bg-teal-50 dark:border-teal-800 dark:bg-teal-950/40",
    circle: "bg-teal-100 dark:bg-teal-900/50",
    icon: "text-teal-600 dark:text-teal-300",
  },
  done: {
    card: "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/40",
    circle: "bg-emerald-100 dark:bg-emerald-900/50",
    icon: "text-emerald-600 dark:text-emerald-300",
  },
};

/**
 * 상태 채널 — 단계색과 분리해 카드 테두리·아이콘 원·오버레이 배지를 결정한다.
 * done/inferred 는 단계색 유지, failed 는 red 로 덮고, skipped 는 단계색을 죽인다.
 */
function statusChrome(stage: StageState): {
  card: string;
  circle: string;
  icon: string;
  overlay: { Icon: LucideIcon; cls: string; spin?: boolean } | null;
} {
  const tone = STAGE_TONE[stage.key];
  switch (stage.status) {
    case "done":
      return {
        card: `border-solid ${tone.card}`,
        circle: tone.circle,
        icon: tone.icon,
        overlay: {
          Icon: Check,
          cls: "bg-emerald-500 text-white dark:bg-emerald-600",
        },
      };
    case "inferred":
      // 단계색 유지 + 진행 추정 스핀 오버레이.
      return {
        card: `border-solid ${tone.card}`,
        circle: tone.circle,
        icon: tone.icon,
        overlay: {
          Icon: Loader2,
          cls: "bg-[var(--accent)] text-[var(--accent-fg)]",
          spin: true,
        },
      };
    case "failed":
      // 실패는 단계색보다 우선해 눈에 들어와야 한다 — red 로 덮는다.
      return {
        card: "border-solid border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/40",
        circle: "bg-red-100 dark:bg-red-900/50",
        icon: "text-red-600 dark:text-red-300",
        overlay: { Icon: X, cls: "bg-red-500 text-white dark:bg-red-600" },
      };
    case "skipped":
      // 기록 없음 — 점선 테두리 + muted 채움으로 단계색을 죽인다.
      return {
        card: "border-dashed border-[var(--border-medium)] bg-[var(--bg-hover)]",
        circle: "bg-[var(--bg-base)]",
        icon: "text-[var(--text-muted)]",
        overlay: {
          Icon: Minus,
          cls: "border border-[var(--border-medium)] bg-[var(--bg-base)] text-[var(--text-muted)]",
        },
      };
    default:
      // pending — 미도달. muted 로 두어 도달한 단계가 돋보이게 한다.
      return {
        card: "border-solid border-[var(--border-subtle)] bg-[var(--bg-base)]",
        circle: "bg-[var(--bg-hover)]",
        icon: "text-[var(--text-muted)] opacity-70",
        overlay: null,
      };
  }
}

/** 커넥터 선 — 진행이 이 지점을 통과했으면(완료/실패/추정) 강조, 아니면 muted. */
function connectorClass(status: StageStatus): string {
  return status === "done" || status === "failed" || status === "inferred"
    ? "bg-emerald-400 dark:bg-emerald-600"
    : "bg-[var(--border-subtle)]";
}

export function PipelineRunFlow({ run }: PipelineRunFlowProps) {
  const t = useTranslations("delivery.pipeline");
  const stages = computePipelineStages(run.events);
  const mismatch = hasModelMismatch(run.events);
  const outcome = run.outcome ?? "unknown";
  const outcomeTone = OUTCOME_TONE[outcome] ?? OUTCOME_TONE.unknown;

  function durationLabel(s: StageState): string | null {
    if (s.durationS === undefined) return null;
    return s.durationDerived
      ? t("durationDerived", { seconds: s.durationS })
      : t("durationSec", { seconds: s.durationS });
  }

  return (
    <div className="flex flex-col gap-3">
      {/* 헤더: 결과 배지 + model_mismatch 경고 */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${outcomeTone}`}
        >
          {t("outcomeLabel")}:{" "}
          {t.has(`outcome.${outcome}`) ? t(`outcome.${outcome}`) : outcome}
        </span>
        {mismatch && (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
            {t("modelMismatch")}
          </span>
        )}
      </div>

      {/* 단계 노드 흐름 — 카드형 노드를 커넥터로 잇고 폭을 고르게 편다. */}
      <ol
        className="flex items-stretch overflow-x-auto pb-1"
        aria-label={t("title")}
      >
        {stages.map((s, i) => {
          const isFirst = i === 0;
          const label = t(`stages.${s.key}`);
          const statusLabel = t(`status.${s.status}`);
          const dur = durationLabel(s);
          const StageIcon = STAGE_ICON[s.key];
          const chrome = statusChrome(s);
          const overlay = chrome.overlay;
          return (
            <Fragment key={s.key}>
              {/* 커넥터 — flex-1 로 늘어나 노드 사이 폭을 채운다(아이콘 원 중심 정렬). */}
              {!isFirst && (
                <li
                  aria-hidden="true"
                  className="flex min-w-[24px] flex-1 items-start"
                >
                  <span
                    className={`mt-[30px] h-0.5 w-full ${connectorClass(s.status)}`}
                  />
                </li>
              )}
              <li
                className={`flex w-[76px] flex-none flex-col items-center gap-1.5 rounded-xl border px-1.5 py-2.5 ${chrome.card}`}
                title={
                  s.status === "inferred"
                    ? t("inferredHint")
                    : s.status === "skipped"
                      ? t("skippedHint")
                      : `${label} · ${statusLabel}`
                }
              >
                {/* 아이콘 원(40px) — 단계 정체성. 우상단 오버레이 배지가 상태를 나타낸다. */}
                <span
                  className={`relative flex h-10 w-10 flex-none items-center justify-center rounded-full ${chrome.circle}`}
                  aria-hidden="true"
                >
                  <StageIcon className={`h-5 w-5 ${chrome.icon}`} />
                  {overlay && (
                    <span
                      className={`absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full ring-2 ring-[var(--bg-base)] ${overlay.cls}`}
                    >
                      <overlay.Icon
                        className={`h-2.5 w-2.5 ${overlay.spin ? "animate-spin" : ""}`}
                      />
                    </span>
                  )}
                </span>
                <span
                  className={`whitespace-nowrap text-[13px] font-semibold ${
                    s.status === "failed"
                      ? "text-red-600 dark:text-red-400"
                      : s.status === "skipped" || s.status === "pending"
                        ? "text-[var(--text-muted)]"
                        : "text-[var(--text-primary)]"
                  }`}
                >
                  {label}
                </span>
                {/* 추정 진행임을 화면에 명시 — 시작 이벤트가 없어 추론한 상태다. */}
                {s.status === "inferred" && (
                  <span className="whitespace-nowrap text-[11px] font-medium text-[var(--accent)]">
                    {t("status.inferred")}
                  </span>
                )}
                {/* 기록 없음 — 실행 여부를 단정하지 않는다(이벤트만 없음). */}
                {s.status === "skipped" && (
                  <span className="whitespace-nowrap text-[11px] font-medium text-[var(--text-muted)]">
                    {t("status.skipped")}
                  </span>
                )}
                {dur && (
                  <span className="whitespace-nowrap font-mono text-[11px] tabular-nums text-[var(--text-muted)]">
                    {dur}
                  </span>
                )}
              </li>
            </Fragment>
          );
        })}
      </ol>

      {/* 유도값 표기 안내 — 노드 소요시간(impl 제외)은 이벤트 시각 차에서 유도됨 */}
      <p className="text-[11px] leading-relaxed text-[var(--text-muted)]">
        {t("derivedHint")}
      </p>
    </div>
  );
}
