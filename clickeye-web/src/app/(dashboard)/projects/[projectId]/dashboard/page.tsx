"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCcw, Loader2 } from "lucide-react";

import { AITeamActivity } from "@/components/dashboard/ai-team-activity";
import { ArtifactStatusChart } from "@/components/dashboard/artifact-status-chart";
import { ProjectTimeline } from "@/components/dashboard/project-timeline";
import { QualityMetrics } from "@/components/dashboard/quality-metrics";
import { useProjectReport } from "@/hooks/use-project-report";

export default function ProjectDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: report, isLoading, error, refetch } = useProjectReport(projectId);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}`}
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white">
              {report?.project_name ?? "프로젝트"} 대시보드
            </h1>
            {report && (
              <p className="text-xs text-slate-500">
                마지막 생성:{" "}
                {new Date(report.generated_at).toLocaleString("ko-KR")}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200 disabled:opacity-50"
        >
          <RefreshCcw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
          새로고침
        </button>
      </div>

      {/* 로딩 */}
      {isLoading && !report && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-violet-400" />
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-center text-sm text-red-400">
          리포트를 불러오지 못했습니다. 다시 시도해 주세요.
        </div>
      )}

      {/* 대시보드 컨텐츠 */}
      {report && (
        <>
          {/* 품질 메트릭 (상단 전체 폭) */}
          <QualityMetrics
            data={report.quality_metrics}
            sessionsTotal={report.sessions_total}
            subtasksTotal={report.subtasks_total}
          />

          {/* 2 컬럼 그리드 */}
          <div className="grid gap-6 lg:grid-cols-2">
            <ArtifactStatusChart data={report.artifact_status_counts} />
            <ProjectTimeline data={report.phase_timeline} />
          </div>

          {/* AI 팀 활동 로그 (하단 전체 폭) */}
          <AITeamActivity data={report.ai_team_activities} />
        </>
      )}
    </div>
  );
}
