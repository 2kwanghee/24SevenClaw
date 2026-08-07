"use client";

import type { ReactNode } from "react";

import { AlertCircle, LayoutDashboard } from "lucide-react";
import { useTranslations } from "next-intl";

import { RoleGuard } from "@/components/common/role-guard";
import { DeliveryBoard } from "@/components/dashboard/delivery-board";
import { DeliveryProgressChart } from "@/components/dashboard/delivery-progress-chart";
import { IntakeTable } from "@/components/dashboard/intake-table";
import { ProjectStatusTable } from "@/components/dashboard/project-status-table";
import { SeatBalanceGauges, SeatRankingTable } from "@/components/dashboard/seat-widgets";
import { BentoCard, BentoGrid } from "@/components/ui/bento";
import { useObservabilitySummary, useSeats } from "@/hooks/use-observability";
import { ApiClientError } from "@/lib/api-client";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

/** 대시보드 세로 섹션 카드 — 딜리버리 보드와 동일한 서피스 톤. */
function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section
      aria-label={title}
      className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function DashboardContent() {
  const t = useTranslations("observability.dashboard");
  const { data, isLoading, error } = useObservabilitySummary();
  // CE-405: 계정 잔량/사용순위 위젯 — 기존 GET /observability/seats 재사용, 요약 데이터와 독립 로딩.
  const { data: seatsData, isLoading: seatsLoading, error: seatsError } = useSeats();

  const summaryError = error && !isFeatureDisabled(error);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
          <LayoutDashboard className="h-5 w-5 text-[var(--accent)]" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("pageTitle")}</h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">{t("pageDescription")}</p>
        </div>
      </div>

      {/* ① 딜리버리 진행 보드 */}
      <DeliveryBoard />

      {/* ② 딜리버리 진행 현황 — 구 성공률 위젯 대체 */}
      <Section title={t("sections.progress")}>
        <DeliveryProgressChart />
      </Section>

      {/* ③ 프로젝트 상태 */}
      <Section title={t("sections.projects")}>
        <ProjectStatusTable countsByStatus={data?.projects_by_status} />
      </Section>

      {/* ④ 인테이크 */}
      <Section title={t("sections.intake")}>
        <IntakeTable />
      </Section>

      {/* ⑤ 최근 딜리버리 이벤트 */}
      <Section title={t("recentDeliveryEvents")}>
        {isLoading ? (
          <p className="text-sm text-[var(--text-muted)]">{t("loading")}</p>
        ) : error && isFeatureDisabled(error) ? (
          <p className="text-sm text-[var(--text-muted)]">{t("featureDisabled")}</p>
        ) : summaryError ? (
          <p className="flex items-center gap-2 text-sm text-[var(--chart-danger)]">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {(error as Error).message || t("error")}
          </p>
        ) : !data || data.recent_delivery_events.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">{t("empty")}</p>
        ) : (
          <ul className="space-y-2">
            {data.recent_delivery_events.map((ev) => (
              <li
                key={ev.id}
                className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-[var(--border-subtle)] pb-2 text-xs last:border-b-0 last:pb-0"
              >
                <span className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-2 py-0.5 font-medium text-[var(--text-secondary)]">
                  {ev.event_type}
                </span>
                <span className="text-[var(--text-muted)]">{ev.actor_type}</span>
                {ev.detail && (
                  <span className="text-[var(--text-secondary)]">{ev.detail}</span>
                )}
                <time className="ml-auto tabular-nums text-[var(--text-muted)]">
                  {new Date(ev.created_at).toLocaleString("ko-KR")}
                </time>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* 계정 위젯 — 5섹션 이후 기존대로 유지 */}
      <BentoGrid className="lg:grid-cols-2">
        <BentoCard title={t("seatBalance.title")} href="/observability/seats">
          {seatsLoading ? (
            <p className="mt-4 text-xs text-[var(--text-muted)]">{t("loading")}</p>
          ) : seatsError ? (
            <p className="mt-4 text-xs text-[var(--text-muted)]">{t("error")}</p>
          ) : (
            <SeatBalanceGauges items={seatsData?.items ?? []} />
          )}
        </BentoCard>

        <BentoCard size="wide" title={t("seatRanking.title")} href="/observability/seats">
          {seatsLoading ? (
            <p className="mt-4 text-xs text-[var(--text-muted)]">{t("loading")}</p>
          ) : seatsError ? (
            <p className="mt-4 text-xs text-[var(--text-muted)]">{t("error")}</p>
          ) : (
            <SeatRankingTable items={seatsData?.items ?? []} />
          )}
        </BentoCard>
      </BentoGrid>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <DashboardContent />
    </RoleGuard>
  );
}
