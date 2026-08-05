"use client";

import { AlertCircle, Bot, GitBranch, Settings2, Ticket, User } from "lucide-react";
import { useTranslations } from "next-intl";

import { BentoCard } from "@/components/ui/bento";
import {
  useIntakeOverview,
  useIntakeTimeline,
  useProjectIntakeTimeline,
} from "@/hooks/use-intake";
import type {
  DeliveryOverviewResponse,
  IntakeResponse,
  IntakeTicketItem,
  IntakeTimelineResponse,
} from "@/lib/api-client";

/**
 * P9: 무인 딜리버리 체인 뷰 — 인테이크 검토 콘솔의 additive 확장.
 *
 * 집계 헤더 / 행 단계 배지 / 전이 타임라인 3개 조각으로 구성된다.
 * 기존 승인·반려 플로우와 독립적이며, 실패해도 본 기능을 막지 않는다.
 */

// ---------------------------------------------------------------------------
// 체인 단계 판정
// ---------------------------------------------------------------------------

/** 체인 단계 — 좁은 것에서 넓은 순(판정 우선순위와 동일) */
export type ChainStage =
  | "rejected"
  | "gate_failed"
  | "verified"
  | "issued"
  | "refined"
  | "refine_skipped"
  | "pending";

/**
 * 인테이크 1건의 체인 단계 판정.
 *
 * tickets_status(발급 이후)가 refine_status(발급 이전)보다 뒤 단계이므로 먼저 본다.
 *
 * refined 와 skipped 를 구분하는 이유: 발급 대기 큐(`list_issue_pending`)와 집계
 * 버킷(`pending_issue`)이 refine_status == "refined" 만 집는다. skipped 는 무인
 * 발급 대상이 아니므로 "발급 대기"로 표시하면 잘못된 기대를 준다.
 */
export function resolveChainStage(item: {
  status: string;
  refine_status: string;
  tickets_status?: string | null;
}): ChainStage {
  if (item.status === "rejected") return "rejected";
  if (item.tickets_status === "gate_failed") return "gate_failed";
  if (item.tickets_status === "verified") return "verified";
  if (item.tickets_status === "issued") return "issued";
  if (item.refine_status === "refined") return "refined";
  if (item.refine_status === "skipped") return "refine_skipped";
  return "pending";
}

/** 단계별 색 — verified 는 accent 강조, gate_failed 는 사람 개입 신호(빨강) */
const STAGE_COLORS: Record<ChainStage, string> = {
  pending:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300",
  refine_skipped:
    "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
  refined:
    "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300",
  issued:
    "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-300",
  verified:
    "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-text)]",
  gate_failed:
    "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300",
  rejected:
    "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
};

/**
 * 집계 타일의 수치 색 — verified/gate_failed 는 full-tint 로 강조하고, 나머지 단계는
 * 배경 대신 수치만 단계색으로 물들여 무채색 그리드를 단계별로 스캔 가능하게 한다.
 * text-X-700/300 수준을 유지해 대비(WCAG AA)를 지킨다.
 */
const STAGE_NUM_TONE: Record<ChainStage, string> = {
  pending: "text-amber-700 dark:text-amber-300",
  refined: "text-blue-700 dark:text-blue-300",
  issued: "text-violet-700 dark:text-violet-300",
  verified: "text-[var(--accent-text)]",
  gate_failed: "text-red-700 dark:text-red-300",
  refine_skipped: "text-[var(--text-muted)]",
  rejected: "text-[var(--text-muted)]",
};

/** 인테이크 행에 붙는 체인 단계 배지 1개 */
export function ChainStageBadge({ item }: { item: IntakeResponse }) {
  const t = useTranslations("intake.chain.stage");
  const stage = resolveChainStage(item);
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-xs font-medium ${STAGE_COLORS[stage]}`}
    >
      {t(stage)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// 집계 헤더
// ---------------------------------------------------------------------------

/** 표시 순서 = 체인 진행 순서. 각 단계가 읽는 overview 필드를 함께 고정한다. */
const OVERVIEW_STAGES: { stage: ChainStage; field: keyof DeliveryOverviewResponse }[] =
  [
    { stage: "pending", field: "pending_refine" },
    { stage: "refined", field: "pending_issue" },
    { stage: "issued", field: "implementing" },
    { stage: "verified", field: "verified" },
    { stage: "gate_failed", field: "gate_failed" },
    { stage: "rejected", field: "rejected" },
  ];

/**
 * 체인 집계 헤더 — 단계별 잔량/결과를 가로 1행으로 보여준다.
 *
 * 보조 정보이므로 로딩은 스켈레톤, 실패는 미표시(null)로 조용히 처리한다.
 */
export function ChainOverviewHeader() {
  const t = useTranslations("intake.chain");
  const tStage = useTranslations("intake.chain.stage");
  const { data, isLoading, error } = useIntakeOverview();

  if (error) return null;

  if (isLoading) {
    return (
      <BentoCard size="wide">
        <div className="flex flex-wrap gap-2" aria-hidden="true">
          {OVERVIEW_STAGES.map((s) => (
            <div
              key={s.stage}
              className="h-14 w-24 animate-pulse rounded-xl bg-[var(--bg-hover)]"
            />
          ))}
        </div>
      </BentoCard>
    );
  }

  if (!data) return null;

  return (
    <BentoCard
      size="wide"
      icon={
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)]">
          <GitBranch className="h-4 w-4 text-[var(--accent)]" />
        </div>
      }
      title={t("title")}
      description={t("description", { total: data.total })}
    >
      <div className="mt-4 flex flex-wrap gap-2">
        {OVERVIEW_STAGES.map(({ stage, field }) => {
          const count = data[field];
          const emphasized =
            (stage === "verified" || stage === "gate_failed") && count > 0;
          return (
            <div
              key={stage}
              className={`min-w-[5.5rem] flex-1 rounded-xl border px-3 py-2 ${
                emphasized
                  ? STAGE_COLORS[stage]
                  : "border-[var(--border-subtle)] bg-[var(--bg-base)]"
              }`}
            >
              <p
                className={`text-xs ${
                  emphasized ? "" : "text-[var(--text-muted)]"
                }`}
              >
                {tStage(stage)}
              </p>
              <p
                className={`mt-0.5 text-xl font-semibold tabular-nums ${
                  emphasized ? "" : STAGE_NUM_TONE[stage]
                }`}
              >
                {count}
              </p>
            </div>
          );
        })}
      </div>
    </BentoCard>
  );
}

// ---------------------------------------------------------------------------
// 전이 타임라인
// ---------------------------------------------------------------------------

/** 이벤트 톤 — 실패 전이는 빨강으로 즉시 눈에 띄게 한다 */
const EVENT_TONES: Record<string, "positive" | "negative"> = {
  refined: "positive",
  accepted: "positive",
  machine_accepted: "positive",
  tickets_issued: "positive",
  verification_passed: "positive",
  callback_sent: "positive",
  rejected: "negative",
  verification_failed: "negative",
  callback_failed: "negative",
};

const DOT_COLORS: Record<"positive" | "negative" | "neutral", string> = {
  positive: "bg-emerald-500",
  negative: "bg-red-500",
  neutral: "bg-[var(--border-medium)]",
};

const ACTOR_ICONS: Record<string, typeof User> = {
  human: User,
  machine: Bot,
  system: Settings2,
};

/**
 * 주체별 색 — 기계/사람/시스템을 색으로 구분한다(CE-373).
 * 전에는 actorType 과 무관하게 muted 단색이었다: 실측 `#a1a1aa` on `#fafafa` 로 대비가
 * 낮아 아이콘을 봐야 주체를 알 수 있었다. 팔레트는 기존 관례를 따른다(violet=기계 계열).
 */
const ACTOR_TONES: Record<string, string> = {
  human:
    "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300",
  machine:
    "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-300",
  system:
    "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300",
};

function ActorBadge({ actorType }: { actorType: string }) {
  const t = useTranslations("intake.chain.timeline.actor");
  const Icon = ACTOR_ICONS[actorType] ?? Settings2;
  const tone = ACTOR_TONES[actorType] ?? ACTOR_TONES.system;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${tone}`}
    >
      <Icon className="h-3 w-3 shrink-0" />
      {t.has(actorType) ? t(actorType) : actorType}
    </span>
  );
}

/** 발급 원장 칩 — CE-### 형태 identifier 나열 */
function TicketChips({ tickets }: { tickets: IntakeTicketItem[] }) {
  const t = useTranslations("intake.chain.tickets");
  return (
    <div className="mt-4 border-t border-[var(--border-subtle)] pt-3">
      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-[var(--text-muted)]">
        <Ticket className="h-3.5 w-3.5" />
        {t("title", { count: tickets.length })}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {/* Linear 정식 URL 은 /{workspace}/issue/{id} 인데 워크스페이스 슬러그 설정이 없어
            링크를 만들 수 없다 — 잘못된 링크(linear.app/issue/…) 대신 원래의 칩 표시로 유지(CE-389 리뷰). */}
        {tickets.map((ticket) => (
          <span
            key={ticket.issue_id || ticket.identifier}
            title={ticket.title}
            className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-base)] px-2 py-0.5 font-mono text-xs text-[var(--text-secondary)]"
          >
            {ticket.identifier}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * 인테이크 1건의 전이 타임라인 — 행 확장 시 렌더된다(그때 처음 조회).
 * 발급 원장이 있으면 타임라인 아래에 identifier 칩을 잇는다.
 *
 * CE-337: `projectId` 가 주어지면 프로젝트 스코프 경로(딜리버리 콘솔)를,
 * 없으면 기존 admin 경로(control_tower:read)를 쓴다. 두 훅을 항상 호출하되
 * `enabled` 로 한쪽만 활성화한다(React 훅 규칙 준수 — 조건부 호출 금지).
 */
export function IntakeTimeline({
  item,
  projectId,
  timelineOverride,
}: {
  item: IntakeResponse;
  projectId?: string;
  /** 목업 모드용 주입 데이터 — 주어지면 fetch 없이 이 값을 렌더한다(단일 컴포넌트 재사용). */
  timelineOverride?: IntakeTimelineResponse;
}) {
  const t = useTranslations("intake.chain.timeline");
  const tEvent = useTranslations("intake.chain.event");
  const useOverride = !!timelineOverride;
  const useProjectScope = !!projectId;
  // 두 훅은 항상 호출하되(React 훅 규칙), override/스코프에 따라 한쪽만 enabled.
  const adminQuery = useIntakeTimeline(item.id, !useProjectScope && !useOverride);
  const projectQuery = useProjectIntakeTimeline(
    projectId ?? "",
    useProjectScope && !useOverride,
  );
  const active = useProjectScope ? projectQuery : adminQuery;
  const data = timelineOverride ?? active.data;
  const isLoading = useOverride ? false : active.isLoading;
  const error = useOverride ? null : active.error;

  const tickets = item.tickets ?? [];

  return (
    <div>
      <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">
        {t("title")}
      </p>

      {isLoading && (
        <p className="text-xs text-[var(--text-muted)]">{t("loading")}</p>
      )}

      {error && (
        <p className="flex items-center gap-1.5 text-xs text-red-700 dark:text-red-300">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {t("error")}
        </p>
      )}

      {data && data.events.length === 0 && (
        <p className="text-xs text-[var(--text-muted)]">{t("empty")}</p>
      )}

      {data && data.events.length > 0 && (
        <ol className="space-y-0">
          {data.events.map((event, index) => {
            const tone = EVENT_TONES[event.event_type] ?? "neutral";
            const isLast = index === data.events.length - 1;
            return (
              <li key={event.id} className="flex gap-3">
                {/* 좌측 레일: 점 + 연결선(마지막 항목은 선 없음) */}
                <div className="flex flex-col items-center pt-1.5">
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${DOT_COLORS[tone]}`}
                  />
                  {!isLast && (
                    <span className="mt-1 w-px flex-1 bg-[var(--border-subtle)]" />
                  )}
                </div>
                <div className={`min-w-0 flex-1 ${isLast ? "" : "pb-3"}`}>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-xs font-medium text-[var(--text-primary)]">
                      {tEvent.has(event.event_type)
                        ? tEvent(event.event_type)
                        : event.event_type}
                    </span>
                    <ActorBadge actorType={event.actor_type} />
                    <time className="text-xs tabular-nums text-[var(--text-muted)]">
                      {event.created_at
                        ? new Date(event.created_at).toLocaleString("ko-KR")
                        : "—"}
                    </time>
                  </div>
                  {event.detail && (
                    <p className="mt-0.5 break-words text-xs leading-relaxed text-[var(--text-secondary)]">
                      {event.detail}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {tickets.length > 0 && <TicketChips tickets={tickets} />}
    </div>
  );
}
