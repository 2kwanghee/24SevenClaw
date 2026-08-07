"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import type { DeliveryBoardTicketItem } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import {
  colorForTicket,
  formatDuration,
  isDangerTicket,
  type StageColumnKey,
} from "./delivery-board-constants";
import { DeliveryBoardFlowAnimation } from "./delivery-board-flow-animation";
import { DeliveryBoardTicketDetailPanel } from "./delivery-board-ticket-detail-panel";

interface DeliveryBoardTicketCardProps {
  ticket: DeliveryBoardTicketItem;
  intakeStatus?: string | null;
  column: StageColumnKey;
}

/** 딜리버리 진행 보드 티켓 카드 — 키·제목·소요시간, failed/Backlog danger 톤,
 * active 이고 직전 단계가 있으면 흐름 애니메이션을 함께 렌더한다.
 * hover 시 보드 데이터만으로 즉시 퀵 툴팁(단계·outcome·소요시간), 클릭 시 Linear 원본 상세 패널. */
export function DeliveryBoardTicketCard({
  ticket,
  intakeStatus,
  column,
}: DeliveryBoardTicketCardProps) {
  const t = useTranslations("observability.dashboard.deliveryBoard");
  const danger = isDangerTicket(ticket, intakeStatus);
  const color = colorForTicket(column, danger);
  const [panelOpen, setPanelOpen] = useState(false);

  const history = ticket.stage_history ?? [];
  // "직전 완료 단계"는 stage_history 의 마지막-1 항목. 배열이 비거나 1개뿐이면 애니메이션 생략.
  const hasPreviousStage = history.length >= 2;
  const showFlow = ticket.active === true && hasPreviousStage;

  const hasDuration = typeof ticket.duration_s === "number" && ticket.duration_s !== null;
  const stageLabel = t(`columns.${column}`);

  return (
    <>
      <div
        data-testid="delivery-board-ticket-card"
        data-danger={danger ? "true" : "false"}
        role="button"
        tabIndex={0}
        aria-haspopup="dialog"
        onClick={() => setPanelOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setPanelOpen(true);
          }
        }}
        className={cn(
          "group relative cursor-pointer rounded-xl border bg-[var(--bg-surface)] px-3 py-2 text-xs shadow-sm",
          "transition-colors hover:bg-[var(--bg-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
          danger ? "border-[var(--chart-danger)]" : "border-[var(--border-subtle)]",
        )}
        style={{ borderLeftColor: color, borderLeftWidth: 3 }}
      >
        {showFlow && <DeliveryBoardFlowAnimation color={color} />}

        <p className="truncate font-medium text-[var(--text-primary)]">
          <span className="mr-1 text-[var(--text-muted)]">{ticket.key}</span>
          {ticket.title}
        </p>

        <div className="mt-1 flex items-center justify-between gap-2">
          {danger ? (
            <span className="rounded-full bg-[var(--chart-danger)]/10 px-1.5 py-0.5 text-[10px] font-medium text-[var(--chart-danger)]">
              {t("failedBadge")}
            </span>
          ) : (
            <span aria-hidden="true" />
          )}
          {hasDuration && (
            <time className="tabular-nums text-[var(--text-muted)]">
              {formatDuration(ticket.duration_s as number, t)}
            </time>
          )}
        </div>

        {/* hover 퀵 툴팁 — 보드 데이터만으로 즉시 표시(원격 호출 없음) */}
        <div
          role="tooltip"
          className={cn(
            "pointer-events-none absolute left-0 top-full z-20 mt-1 w-max max-w-[16rem] rounded-lg border border-[var(--border-subtle)]",
            "bg-[var(--bg-surface)] px-2.5 py-1.5 text-[11px] shadow-lg",
            "opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100",
          )}
        >
          <p className="font-medium text-[var(--text-primary)]">{ticket.title}</p>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[var(--text-muted)]">
            <span>
              {t("tooltip.stage")}: {stageLabel}
            </span>
            {ticket.outcome && (
              <span>
                {t("tooltip.outcome")}: {ticket.outcome}
              </span>
            )}
            {hasDuration && (
              <span>
                {t("tooltip.duration")}: {formatDuration(ticket.duration_s as number, t)}
              </span>
            )}
          </div>
        </div>
      </div>

      <DeliveryBoardTicketDetailPanel
        ticket={ticket}
        open={panelOpen}
        onClose={() => setPanelOpen(false)}
      />
    </>
  );
}
