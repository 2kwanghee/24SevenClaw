"use client";

import { Cpu, ThumbsUp, FileCheck } from "lucide-react";

import type { ProjectKPIResponse, QualityMetrics } from "@/lib/api-client";

interface KpiCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  accent: string;
  bgAccent: string;
}

function KpiCard({ icon, label, value, sub, accent, bgAccent }: KpiCardProps) {
  return (
    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6">
      <div className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl ${bgAccent}`}>
        <div className={accent}>{icon}</div>
      </div>
      <p className="text-3xl font-bold text-slate-100">{value}</p>
      <p className="mt-1 text-sm font-medium text-slate-300">{label}</p>
      <p className="mt-0.5 text-xs text-slate-500">{sub}</p>
    </div>
  );
}

interface KpiHeroProps {
  kpi: ProjectKPIResponse;
  quality: QualityMetrics;
}

export function KpiHero({ kpi, quality }: KpiHeroProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <KpiCard
        icon={<Cpu className="h-5 w-5" />}
        label="자동화율"
        value={`${Math.round(kpi.automation_rate)}%`}
        sub="완료된 서브태스크 비율"
        accent="text-violet-400"
        bgAccent="bg-violet-500/10"
      />
      <KpiCard
        icon={<ThumbsUp className="h-5 w-5" />}
        label="리뷰 수락율"
        value={`${Math.round(kpi.review_acceptance_rate)}%`}
        sub="수정 없이 통과된 산출물"
        accent="text-emerald-400"
        bgAccent="bg-emerald-500/10"
      />
      <KpiCard
        icon={<FileCheck className="h-5 w-5" />}
        label="산출물"
        value={`${quality.released_artifacts}/${quality.total_artifacts}`}
        sub={`배포율 ${quality.total_artifacts > 0 ? Math.round((quality.released_artifacts / quality.total_artifacts) * 100) : 0}%`}
        accent="text-cyan-400"
        bgAccent="bg-cyan-500/10"
      />
    </div>
  );
}
