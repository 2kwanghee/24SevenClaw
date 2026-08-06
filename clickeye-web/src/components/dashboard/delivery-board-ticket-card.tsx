"use client";

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

interface DeliveryBoardTicketCardProps {
  ticket: DeliveryBoardTicketItem;
  intakeStatus?: string | null;
  column: StageColumnKey;
}

/** 딜리버리 진행 보드 티켓 카드 — 키·제목·소요시간, failed/Backlog danger 톤,
 * active 이고 직전 단계가 있으면 흐름 애니메이션을 함께 렌더한다. */
export function DeliveryBoardTicketCard({
  ticket,
  intakeStatus,
  column,
}: DeliveryBoardTicketCardProps) {
  const t = useTranslations("observability.dashboard.deliveryBoard");
  const danger = isDangerTicket(ticket, intakeStatus);
  const color = colorForTicket(column, danger);

  const history = ticket.stage_history ?? [];
  // "직전 완료 단계"는 stage_history 의 마지막-1 항목. 배열이 비거나 1개뿐이면 애니메이션 생략.
  const hasPreviousStage = history.length >= 2;
  const showFlow = ticket.active === true && hasPreviousStage;

  return (
    <div
      data-testid="delivery-board-ticket-card"
      data-danger={danger ? "true" : "false"}
      className={cn(
        "relative rounded-xl border bg-[var(--bg-surface)] px-3 py-2 text-xs shadow-sm",
        danger ? "border-[var(--chart-danger)]" : "border-[var(--border-subtle)]",
      )}
      style={{ borderLeftColor: color, borderLeftWidth: 3 }}
    >
      {showFlow && <DeliveryBoardFlowAnimation color={color} />}

      <p className="truncate font-medium text-[var(--text-primary)]" title={ticket.title}>
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
        {typeof ticket.duration_s === "number" && ticket.duration_s !== null && (
          <time className="tabular-nums text-[var(--text-muted)]">
            {formatDuration(ticket.duration_s, t)}
          </time>
        )}
      </div>
    </div>
  );
}
