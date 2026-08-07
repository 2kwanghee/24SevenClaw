"use client";

import { useMemo, useState } from "react";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useIntakeList } from "@/hooks/use-intake";
import { ApiClientError, type IntakeResponse } from "@/lib/api-client";
import { cn } from "@/lib/utils";

function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

/** 인테이크 실존 상태값 → 뱃지 색(기존 토큰 재사용). */
const STATUS_COLORS: Record<string, string> = {
  accepted: "var(--chart-info)",
  rejected: "var(--text-muted)",
  pending_review: "var(--chart-warning)",
};

function statusColor(key: string): string {
  return STATUS_COLORS[key] ?? "var(--text-muted)";
}

const KNOWN_STATUS = new Set(Object.keys(STATUS_COLORS));

/** 알려진 상태만 번역, 미지 값은 원본 문자열로 폴백(t() 미스 키 예외 방지). */
function statusLabel(t: ReturnType<typeof useTranslations>, key: string): string {
  return KNOWN_STATUS.has(key) ? t(`status.${key}`) : key;
}

type IntakeTab = "all" | "accepted" | "rejected" | "pending";

const TAB_STATUS: Record<Exclude<IntakeTab, "all">, string> = {
  accepted: "accepted",
  rejected: "rejected",
  pending: "pending_review",
};

const TABS: IntakeTab[] = ["all", "accepted", "rejected", "pending"];

/**
 * 인테이크 테이블 — 탭(전체/승인/거부/검토중) + 리스트 + 인테이크 관리 바로가기.
 * 기존 useIntakeList()(GET /intake) 를 재사용해 전체를 1회 조회하고 탭은 클라이언트에서 필터한다.
 */
export function IntakeTable() {
  const t = useTranslations("observability.dashboard");
  const [tab, setTab] = useState<IntakeTab>("all");
  const { data, isLoading, error } = useIntakeList();

  const items = useMemo<IntakeResponse[]>(() => data ?? [], [data]);

  const counts = useMemo(() => {
    return {
      all: items.length,
      accepted: items.filter((i) => i.status === TAB_STATUS.accepted).length,
      rejected: items.filter((i) => i.status === TAB_STATUS.rejected).length,
      pending: items.filter((i) => i.status === TAB_STATUS.pending).length,
    };
  }, [items]);

  const filtered = useMemo(() => {
    if (tab === "all") return items;
    return items.filter((i) => i.status === TAB_STATUS[tab]);
  }, [items, tab]);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div
          role="tablist"
          aria-label={t("intakeTable.tabsLabel")}
          className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-0.5"
        >
          {TABS.map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                tab === key
                  ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm"
                  : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]",
              )}
            >
              {t(`intakeTable.tabs.${key}`)}
              <span className="ml-1 tabular-nums text-[var(--text-muted)]">{counts[key]}</span>
            </button>
          ))}
        </div>

        <Link
          href="/admin/intake"
          className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
        >
          {t("intakeTable.goto")}
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {isLoading ? (
        <p className="text-sm text-[var(--text-muted)]">{t("loading")}</p>
      ) : error && isFeatureDisabled(error) ? (
        <p className="text-sm text-[var(--text-muted)]">{t("featureDisabled")}</p>
      ) : error ? (
        <p className="text-sm text-[var(--chart-danger)]">{t("error")}</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">{t("intakeTable.empty")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] text-left text-xs text-[var(--text-muted)]">
                <th className="py-1.5 pr-2 font-medium">{t("intakeTable.colTitle")}</th>
                <th className="py-1.5 pr-2 font-medium">{t("intakeTable.colStatus")}</th>
                <th className="py-1.5 pr-2 font-medium">{t("intakeTable.colTickets")}</th>
                <th className="py-1.5 text-right font-medium">{t("intakeTable.colReceived")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const issued = item.tickets_status !== "none";
                return (
                  <tr
                    key={item.id}
                    className="border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--bg-hover)]"
                  >
                    <td className="py-1.5 pr-2 text-[var(--text-primary)]">{item.title}</td>
                    <td className="py-1.5 pr-2">
                      <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: statusColor(item.status) }}
                        />
                        {statusLabel(t, item.status)}
                      </span>
                    </td>
                    <td className="py-1.5 pr-2 text-xs text-[var(--text-secondary)]">
                      {issued ? t("intakeTable.ticketsIssued") : t("intakeTable.ticketsNone")}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-[var(--text-muted)]">
                      {item.created_at
                        ? new Date(item.created_at).toLocaleDateString("ko-KR")
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
