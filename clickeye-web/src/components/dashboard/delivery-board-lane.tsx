"use client";

import { useTranslations } from "next-intl";

import type { DeliveryBoardProjectItem, DeliveryBoardTicketItem } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { STAGE_COLUMNS, resolveTicketColumn, type StageColumnKey } from "./delivery-board-constants";
import { DeliveryBoardTicketCard } from "./delivery-board-ticket-card";

interface DeliveryBoardLaneProps {
  project: DeliveryBoardProjectItem;
}

type CheckpointKey = "received_at" | "refined_at" | "accepted_at" | "issued_at";

/** 프로젝트 레벨 4단계 체크포인트 — 티켓이 위치하는 8컬럼 축과는 별개 트랙. */
const CHECKPOINTS: CheckpointKey[] = [
  "received_at",
  "refined_at",
  "accepted_at",
  "issued_at",
];

function groupByColumn(
  tickets: DeliveryBoardTicketItem[],
): Map<StageColumnKey, DeliveryBoardTicketItem[]> {
  const byColumn = new Map<StageColumnKey, DeliveryBoardTicketItem[]>();
  for (const col of STAGE_COLUMNS) byColumn.set(col, []);
  for (const ticket of tickets) {
    const column = resolveTicketColumn(ticket);
    byColumn.get(column)?.push(ticket);
  }
  return byColumn;
}

/** 프로젝트 1행(스윔레인) — 프로젝트명+intake_status 뱃지, 4단계 체크 도트,
 * 해당 레인 티켓을 매핑 컬럼에 배치. md 이상은 가로 8컬럼, 모바일은 세로 스택. */
export function DeliveryBoardLane({ project }: DeliveryBoardLaneProps) {
  const t = useTranslations("observability.dashboard.deliveryBoard");
  const tickets = project.tickets ?? [];
  const stages = project.stages ?? {};
  const byColumn = groupByColumn(tickets);

  return (
    <div
      data-testid="delivery-board-lane"
      className="border-b border-[var(--border-subtle)] py-3 last:border-b-0"
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <p className="truncate text-sm font-semibold text-[var(--text-primary)]">
          {project.name}
        </p>
        {project.intake_status && (
          <span className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-secondary)]">
            {project.intake_status}
          </span>
        )}
        <div className="ml-auto flex items-center gap-1" aria-hidden="true">
          {CHECKPOINTS.map((key) => {
            const reached = Boolean(stages[key]);
            return (
              <span
                key={key}
                title={t(`checkpoint.${key}`)}
                className={cn(
                  "h-2 w-2 rounded-full",
                  reached ? "bg-[var(--accent)]" : "bg-[var(--border-subtle)]",
                )}
              />
            );
          })}
        </div>
      </div>

      {/* md 이상: 가로 8컬럼 스윔레인 */}
      <div className="hidden min-w-[720px] grid-cols-8 gap-2 md:grid">
        {STAGE_COLUMNS.map((col) => (
          <div key={col} className="flex min-h-[2.5rem] flex-col gap-2">
            {byColumn.get(col)?.map((ticket) => (
              <DeliveryBoardTicketCard
                key={ticket.key}
                ticket={ticket}
                intakeStatus={project.intake_status}
                column={col}
              />
            ))}
          </div>
        ))}
      </div>

      {/* 모바일: 프로젝트별 세로 스택 카드 리스트 */}
      <div className="flex flex-col gap-2 md:hidden">
        {tickets.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">{t("laneEmpty")}</p>
        ) : (
          tickets.map((ticket) => (
            <DeliveryBoardTicketCard
              key={ticket.key}
              ticket={ticket}
              intakeStatus={project.intake_status}
              column={resolveTicketColumn(ticket)}
            />
          ))
        )}
      </div>
    </div>
  );
}
