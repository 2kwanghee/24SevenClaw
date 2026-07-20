"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCcw, Loader2, BarChart3 } from "lucide-react";

import { AutomationBreakdown } from "@/components/dashboard/automation-breakdown";
import { KpiHero } from "@/components/dashboard/kpi-hero";
import { PhaseVelocityChart } from "@/components/dashboard/phase-velocity-chart";
import { ValueComparison } from "@/components/dashboard/value-comparison";
import { WeeklyThroughput } from "@/components/dashboard/weekly-throughput";
import { useProjectKPI } from "@/hooks/use-project-kpi";
import { useProjectReport } from "@/hooks/use-project-report";

export default function ProjectInsightsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const {
    data: kpi,
    isLoading: kpiLoading,
    error: kpiError,
    refetch: refetchKpi,
  } = useProjectKPI(projectId);
  const {
    data: report,
    isLoading: reportLoading,
    refetch: refetchReport,
  } = useProjectReport(projectId);

  const isLoading = kpiLoading || reportLoading;
  const handleRefresh = () => {
    refetchKpi();
    refetchReport();
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}`}
            className="rounded-lg p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-[var(--text-muted)]" />
              <h1 className="text-lg font-bold text-[var(--text-primary)]">
                {kpi?.project_name ?? report?.project_name ?? "프로젝트"} KPI 인사이트
              </h1>
            </div>
            {kpi && (
              <p className="text-xs text-[var(--text-muted)]">
                마지막 집계:{" "}
                {new Date(kpi.generated_at).toLocaleString("ko-KR")}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)] disabled:opacity-50"
        >
          <RefreshCcw
            className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`}
          />
          새로고침
        </button>
      </div>

      {/* 로딩 */}
      {isLoading && !kpi && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" />
        </div>
      )}

      {/* 에러 */}
      {kpiError && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-700">
          KPI 데이터를 불러오지 못했습니다. 다시 시도해 주세요.
        </div>
      )}

      {/* KPI 컨텐츠 */}
      {kpi && report && (
        <>
          {/* 히어로 카운터 카드 */}
          <KpiHero kpi={kpi} quality={report.quality_metrics} />

          {/* 시간 비교 */}
          <ValueComparison avgPhaseDuration={kpi.avg_phase_duration} />

          {/* 2컬럼: 단계별 소요시간 + AI/사람 비율 */}
          <div className="grid gap-6 lg:grid-cols-2">
            <PhaseVelocityChart data={kpi.avg_phase_duration} />
            <AutomationBreakdown automationRate={kpi.automation_rate} />
          </div>

          {/* 주간 처리량 */}
          <WeeklyThroughput data={kpi.throughput_per_week} />
        </>
      )}

      {/* KPI만 있고 report 아직 로딩 중 */}
      {kpi && !report && !reportLoading && (
        <>
          <KpiHero
            kpi={kpi}
            quality={{
              total_artifacts: 0,
              released_artifacts: 0,
              avg_review_score: null,
              avg_revision_count: 0,
              review_rounds_total: 0,
              review_completion_rate: 0,
            }}
          />
          <ValueComparison avgPhaseDuration={kpi.avg_phase_duration} />
          <div className="grid gap-6 lg:grid-cols-2">
            <PhaseVelocityChart data={kpi.avg_phase_duration} />
            <AutomationBreakdown automationRate={kpi.automation_rate} />
          </div>
          <WeeklyThroughput data={kpi.throughput_per_week} />
        </>
      )}
    </div>
  );
}
