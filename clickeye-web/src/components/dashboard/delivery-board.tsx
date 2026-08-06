"use client";

import { useTranslations } from "next-intl";

import { useDeliveryBoard } from "@/hooks/use-observability";
import { ApiClientError } from "@/lib/api-client";

import { STAGE_COLUMNS } from "./delivery-board-constants";
import { DeliveryBoardLane } from "./delivery-board-lane";
import { DeliveryBoardSkeleton } from "./delivery-board-skeleton";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

/** 딜리버리 진행 보드 — 대시보드 홈 최상단, 전폭 스윔레인(프로젝트) × 8단계 카드 보드 (CE-411/CE-412). */
export function DeliveryBoard() {
  const t = useTranslations("observability.dashboard.deliveryBoard");
  const { data, isLoading, error } = useDeliveryBoard();

  const projects = data?.projects ?? [];

  return (
    <section
      aria-label={t("title")}
      className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">{t("title")}</h2>
      </div>

      {isLoading && <DeliveryBoardSkeleton />}

      {error && isFeatureDisabled(error) && (
        <p className="py-6 text-center text-sm text-[var(--text-muted)]">
          {t("featureDisabled")}
        </p>
      )}

      {error && !isFeatureDisabled(error) && (
        <p className="py-6 text-center text-sm text-[var(--chart-danger)]">{t("error")}</p>
      )}

      {data && projects.length === 0 && (
        <p className="py-6 text-center text-sm text-[var(--text-muted)]">{t("empty")}</p>
      )}

      {data && projects.length > 0 && (
        <div className="md:overflow-x-auto">
          <div className="md:min-w-[720px]">
            <div className="hidden grid-cols-8 gap-2 border-b border-[var(--border-subtle)] pb-2 md:grid">
              {STAGE_COLUMNS.map((col) => (
                <p
                  key={col}
                  className="sticky top-0 truncate text-xs font-medium text-[var(--text-secondary)]"
                >
                  {t(`columns.${col}`)}
                </p>
              ))}
            </div>

            {projects.map((project) => (
              <DeliveryBoardLane key={project.project_id} project={project} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
