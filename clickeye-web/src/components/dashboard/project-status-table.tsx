"use client";

import { useMemo, useState } from "react";

import { useTranslations } from "next-intl";

import { useProjectSummary } from "@/hooks/use-observability";
import { useProjects } from "@/hooks/use-projects";
import type { ProjectResponse } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/** 프로젝트 실존 상태값 → 뱃지 색(신규 CSS 변수 추가 없이 기존 토큰 재사용). */
const STATUS_COLORS: Record<string, string> = {
  active: "var(--accent)",
  archived: "var(--text-muted)",
  deleted: "var(--chart-danger)",
};

function statusColor(key: string): string {
  return STATUS_COLORS[key] ?? "var(--text-muted)";
}

/** 상단 탭 → 실존 프로젝트 상태값 매핑. all 은 필터 없음. */
type ProjectTab = "all" | "completed" | "inProgress" | "notStarted";

const TAB_STATUS: Record<Exclude<ProjectTab, "all">, string> = {
  completed: "archived",
  inProgress: "active",
  notStarted: "deleted",
};

const TABS: ProjectTab[] = ["all", "completed", "inProgress", "notStarted"];

/** 프로젝트 개별 상세(hover) — 토큰 합계·활동 기간·사용 계정 목록. CE-402 summary API 소비. */
function ProjectDetailCard({ projectId }: { projectId: string }) {
  const t = useTranslations("observability.dashboard.projectDetail");
  const { data, isLoading, error } = useProjectSummary(projectId, true);

  if (isLoading) {
    return <p className="text-xs text-[var(--text-muted)]">{t("loading")}</p>;
  }
  if (error || !data) {
    return <p className="text-xs text-[var(--text-muted)]">{t("error")}</p>;
  }

  const accounts = data.seats
    .map((s) => s.account_email)
    .filter((email): email is string => !!email);

  return (
    <div className="space-y-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-2.5 text-xs">
      <p className="text-[var(--text-secondary)]">
        {t("tokens")}:{" "}
        <span className="tabular-nums font-medium text-[var(--text-primary)]">
          {data.total_input_tokens + data.total_output_tokens}
        </span>
      </p>
      <p className="text-[var(--text-secondary)]">
        {t("period")}:{" "}
        <span className="text-[var(--text-primary)]">
          {data.first_activity_at
            ? new Date(data.first_activity_at).toLocaleDateString("ko-KR")
            : "—"}
          {" ~ "}
          {data.last_activity_at
            ? new Date(data.last_activity_at).toLocaleDateString("ko-KR")
            : "—"}
        </span>
      </p>
      <p className="text-[var(--text-secondary)]">
        {t("accounts")}:{" "}
        <span className="text-[var(--text-primary)]">
          {accounts.length > 0 ? accounts.join(", ") : t("accountsPending")}
        </span>
      </p>
    </div>
  );
}

interface ProjectStatusTableProps {
  /** 요약 API projects_by_status — 탭 뱃지 카운트 소스(합계값, project_id 미포함). */
  countsByStatus?: Record<string, number>;
}

/**
 * 프로젝트 상태 테이블 — 탭(전체/완료/진행중/미진행) + 리스트.
 * 목록은 useProjects(limit 100), 탭 뱃지 카운트는 요약 API projects_by_status 를 사용한다.
 * deleted(미진행) 상태는 목록 API 가 soft-delete 를 제외해 반환하지 않으므로 목록은 비고 안내로 폴백.
 */
export function ProjectStatusTable({ countsByStatus }: ProjectStatusTableProps) {
  const t = useTranslations("observability.dashboard");
  const [tab, setTab] = useState<ProjectTab>("all");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const { data, isLoading } = useProjects({ limit: 100 });

  const projects = useMemo(() => data?.items ?? [], [data]);

  const counts = useMemo(() => {
    const by = countsByStatus ?? {};
    return {
      all: Object.values(by).reduce((sum, v) => sum + v, 0),
      completed: by[TAB_STATUS.completed] ?? 0,
      inProgress: by[TAB_STATUS.inProgress] ?? 0,
      notStarted: by[TAB_STATUS.notStarted] ?? 0,
    };
  }, [countsByStatus]);

  const filtered: ProjectResponse[] = useMemo(() => {
    if (tab === "all") return projects;
    return projects.filter((p) => p.status === TAB_STATUS[tab]);
  }, [projects, tab]);

  return (
    <div>
      <div
        role="tablist"
        aria-label={t("projectTable.tabsLabel")}
        className="mb-3 inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-0.5"
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
            {t(`projectTable.tabs.${key}`)}
            <span className="ml-1 tabular-nums text-[var(--text-muted)]">{counts[key]}</span>
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-sm text-[var(--text-muted)]">{t("loading")}</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">
          {tab === "notStarted" ? t("projectDetail.noList") : t("projectTable.empty")}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] text-left text-xs text-[var(--text-muted)]">
                <th className="py-1.5 pr-2 font-medium">{t("projectTable.colName")}</th>
                <th className="py-1.5 pr-2 font-medium">{t("projectTable.colStatus")}</th>
                <th className="py-1.5 text-right font-medium">{t("projectTable.colCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr
                  key={p.id}
                  onMouseEnter={() => setHoveredId(p.id)}
                  onMouseLeave={() =>
                    setHoveredId((cur) => (cur === p.id ? null : cur))
                  }
                  onFocus={() => setHoveredId(p.id)}
                  tabIndex={0}
                  className="border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--bg-hover)]"
                >
                  <td className="py-1.5 pr-2 text-[var(--text-primary)]">{p.name}</td>
                  <td className="py-1.5 pr-2">
                    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: statusColor(p.status) }}
                      />
                      {t(`status.${p.status}`)}
                    </span>
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-[var(--text-muted)]">
                    {new Date(p.created_at).toLocaleDateString("ko-KR")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {hoveredId && (
            <div className="mt-2">
              <ProjectDetailCard projectId={hoveredId} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
