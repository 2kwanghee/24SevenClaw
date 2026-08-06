import type { DeliveryBoardTicketItem } from "@/lib/api-client";

/**
 * 딜리버리 진행 보드 8단계 컬럼 — 접수→정제→승인→발급→구현→QA→게이트→완료.
 *
 * 백엔드(clickeye-api app/services/observability_service.py)는 이 8키를 계약상 보장하지
 * 않고 자유 문자열(stage)을 내려준다. 프론트가 이 상수와 매핑 함수로 8컬럼 축을 스스로 정의한다.
 */
export const STAGE_COLUMNS = [
  "received",
  "refined",
  "accepted",
  "issued",
  "implementing",
  "qa",
  "gate",
  "done",
] as const;

export type StageColumnKey = (typeof STAGE_COLUMNS)[number];

/** 백엔드 자유 문자열 stage → 8단계 컬럼 키 별칭 목록.
 * observability_service.py `_BOARD_STAGE_BY_EVENT` 기준(issued/refining/implementing/qa/gate/done/failed) +
 * 향후 확장 가능성(received/accepted/merged/pr/pushed)을 함께 수용한다. */
const STAGE_ALIASES: Record<StageColumnKey, string[]> = {
  received: ["received"],
  refined: ["refined", "refining"],
  accepted: ["accepted"],
  issued: ["issued"],
  implementing: ["implementing", "impl", "in_progress"],
  qa: ["qa"],
  gate: ["gate"],
  done: ["done", "failed", "merged", "pr", "pushed"],
};

const STAGE_LOOKUP: Record<string, StageColumnKey> = Object.entries(
  STAGE_ALIASES,
).reduce<Record<string, StageColumnKey>>((acc, [column, aliases]) => {
  for (const alias of aliases) {
    acc[alias] = column as StageColumnKey;
  }
  return acc;
}, {});

/** stage 문자열 → 8단계 컬럼 키. 매핑 불가 시 null(크래시 대신 호출부가 폴백 처리). */
export function mapStageToColumn(
  stage: string | null | undefined,
): StageColumnKey | null {
  if (!stage) return null;
  return STAGE_LOOKUP[stage] ?? null;
}

/**
 * 티켓의 현재 표시 컬럼을 결정한다.
 * 1) 현재 stage 가 매핑되면 그대로 사용.
 * 2) 매핑 불가(미지 값) → console.warn 후 stage_history 를 최신순으로 훑어 마지막으로
 *    매핑 가능했던 컬럼을 그대로 유지(크래시 방지, 계약 미보장 자유 문자열 대응).
 * 3) 이력에도 매핑 가능한 값이 전혀 없으면 fallback(기본 첫 컬럼)으로 유지.
 */
export function resolveTicketColumn(
  ticket: Pick<DeliveryBoardTicketItem, "key" | "stage" | "stage_history">,
  fallback: StageColumnKey = STAGE_COLUMNS[0],
): StageColumnKey {
  const direct = mapStageToColumn(ticket.stage);
  if (direct) return direct;

  console.warn(
    `[delivery-board] 알 수 없는 stage "${ticket.stage}" (ticket=${ticket.key}) — 직전 알려진 컬럼을 유지합니다.`,
  );

  const history = ticket.stage_history ?? [];
  for (let i = history.length - 1; i >= 0; i -= 1) {
    const mapped = mapStageToColumn(history[i]?.stage);
    if (mapped) return mapped;
  }
  return fallback;
}

/** danger 톤 판정 — 백엔드가 계산한 stage=failed(성공 도메인 밖 outcome 전체를 여기로
 * 묶는다: unknown/demoted/None 포함, observability_service.py `_derive_ticket_progress`
 * 참고) 또는 프로젝트 intake_status=Backlog. outcome 필드는 원본 문자열이 그대로 실려오므로
 * "failed" 리터럴만 보면 unknown/demoted 케이스를 놓친다 — stage 로 판정해야 한다. */
export function isDangerTicket(
  ticket: Pick<DeliveryBoardTicketItem, "stage">,
  intakeStatus: string | null | undefined,
): boolean {
  return ticket.stage === "failed" || intakeStatus === "Backlog";
}

/** 컬럼별 강조 톤 — 기존 --chart- 계열 / --accent 토큰만 재사용(신규 CSS 변수 추가 금지). */
export const COLUMN_COLORS: Record<StageColumnKey, string> = {
  received: "var(--chart-info)",
  refined: "var(--chart-info)",
  accepted: "var(--accent)",
  issued: "var(--accent)",
  implementing: "var(--accent)",
  qa: "var(--chart-warning)",
  gate: "var(--chart-warning)",
  done: "var(--accent)",
};

export const DANGER_COLOR = "var(--chart-danger)";

/** 티켓 카드 강조색 — danger 티켓은 항상 danger 톤 고정, 그 외엔 현재 컬럼 톤. */
export function colorForTicket(column: StageColumnKey, danger: boolean): string {
  return danger ? DANGER_COLOR : COLUMN_COLORS[column];
}

type TranslateFn = (
  key: string,
  values?: Record<string, string | number>,
) => string;

/** duration_s(초) → "3분"/"1시간 20분" 류 사람이 읽는 표기. 번역 키는
 * observability.dashboard.deliveryBoard.duration.* (ko/en messages) 를 사용한다. */
export function formatDuration(seconds: number, t: TranslateFn): string {
  const safeSeconds = Math.max(0, Math.round(seconds));
  if (safeSeconds < 60) {
    return t("duration.seconds", { value: safeSeconds });
  }

  const totalMinutes = Math.round(safeSeconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) {
    return t("duration.minutes", { value: minutes });
  }
  if (minutes === 0) {
    return t("duration.hours", { hours });
  }
  return t("duration.hoursMinutes", { hours, minutes });
}
