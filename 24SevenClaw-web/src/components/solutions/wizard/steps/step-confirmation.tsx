"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { useSession } from "next-auth/react";
import {
  Building2,
  Cpu,
  UserCircle2,
  Bot,
  Wrench,
  Webhook,
  Server,
  Puzzle,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { pmProfiles, type PMProfileWithMetrics } from "@/lib/api-client";
import { PMRatingStars } from "../pm-rating-stars";
import { PrototypePreview } from "../prototype-preview";

// ---------------------------------------------------------------------------
// 레이블 맵
// ---------------------------------------------------------------------------

const BUSINESS_TYPE_LABELS: Record<string, string> = {
  b2b: "B2B",
  b2c: "B2C",
  b2b2c: "B2B2C",
  internal: "내부 도구",
};

const INDUSTRY_LABELS: Record<string, string> = {
  it: "IT/소프트웨어",
  fintech: "핀테크/금융",
  ecommerce: "이커머스",
  healthcare: "헬스케어",
  education: "교육",
  manufacturing: "제조",
  logistics: "물류",
  marketing: "마케팅",
  game: "게임",
  other: "기타",
};

const SOLUTION_TYPE_LABELS: Record<string, string> = {
  saas: "SaaS",
  "rest-api": "REST API",
  fullstack: "풀스택",
  "internal-tool": "내부 도구",
  mvp: "MVP",
  custom: "커스텀",
};

// ---------------------------------------------------------------------------
// PM 구성 요소 수 계산 (pm-composition-view.tsx 와 동일 로직)
// ---------------------------------------------------------------------------

const MCP_SKILL_NAMES = new Set([
  "linear",
  "github",
  "slack",
  "jira",
  "notion",
  "telegram",
  "figma",
]);

function deriveCompositionCounts(profile: PMProfileWithMetrics) {
  const traits = profile.personality as Record<string, unknown>;

  const agents =
    (traits.agents as string[] | undefined) ??
    profile.specialties
      .slice(0, 3)
      .map((a) => a.toLowerCase().replace(/\s+/g, "-"));
  const skills =
    (traits.skills as string[] | undefined) ?? profile.specialties;
  const hooks =
    (traits.hooks as string[] | undefined) ?? ["pre-commit", "test-runner"];
  const mcp_servers =
    (traits.mcp_servers as string[] | undefined) ??
    profile.specialties.filter((s) => MCP_SKILL_NAMES.has(s.toLowerCase()));
  const plugins =
    (traits.plugins as string[] | undefined) ?? ["code-review"];

  return {
    agents: agents.length,
    skills: skills.length,
    hooks: hooks.length,
    mcp_servers: mcp_servers.length,
    plugins: plugins.length,
  };
}

// ---------------------------------------------------------------------------
// 하위 컴포넌트
// ---------------------------------------------------------------------------

interface SummaryRowProps {
  label: string;
  value: string;
}

function SummaryRow({ label, value }: SummaryRowProps) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="shrink-0 text-xs text-slate-500">{label}</span>
      <span className="text-right text-xs text-slate-300">{value}</span>
    </div>
  );
}

interface ReSelectorProps {
  stepIndex: number;
  label: string;
}

function ReSelector({ stepIndex, label }: ReSelectorProps) {
  const goToStep = useSolutionWizardStore((s) => s.goToStep);
  return (
    <button
      type="button"
      onClick={() => goToStep(stepIndex)}
      className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
      aria-label={`${label} 단계로 이동`}
    >
      <ArrowLeft className="h-3 w-3" aria-hidden="true" />
      {label}
    </button>
  );
}

interface CompositionCountBadgeProps {
  icon: ComponentType<{ className?: string }>;
  label: string;
  count: number;
  color: string;
  bg: string;
}

function CompositionCountBadge({
  icon: Icon,
  label,
  count,
  color,
  bg,
}: CompositionCountBadgeProps) {
  return (
    <div className={cn("flex flex-col items-center gap-1 rounded-lg py-2", bg)}>
      <Icon className={cn("h-3.5 w-3.5", color)} aria-hidden="true" />
      <span className="text-sm font-semibold text-white">{count}</span>
      <span className="text-[10px] leading-none text-slate-500">{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StepConfirmation — Step 7 최종 확인
// ---------------------------------------------------------------------------

export function StepConfirmation() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const data = useSolutionWizardStore((s) => s.data);
  const { company, prototypes, pm } = data;

  const selectedProto = prototypes.generatedPrototypes.find(
    (p) => p.id === prototypes.selectedPrototypeId,
  );

  const [pmProfile, setPmProfile] = useState<PMProfileWithMetrics | null>(null);

  useEffect(() => {
    if (!token || !pm.selectedPmProfileId) return;
    void pmProfiles
      .get(token, pm.selectedPmProfileId)
      .then(setPmProfile)
      .catch(() => {});
  }, [token, pm.selectedPmProfileId]);

  const compositionCounts = pmProfile ? deriveCompositionCounts(pmProfile) : null;

  return (
    <div className="space-y-4" role="region" aria-label="최종 확인">
      {/* -- 회사 정보 -- */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <Building2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
            회사 정보
          </h3>
          <ReSelector stepIndex={0} label="재설정" />
        </div>
        <div className="space-y-2">
          <SummaryRow label="회사명" value={company.companyName || "미설정"} />
          <SummaryRow
            label="업종"
            value={INDUSTRY_LABELS[company.industry ?? ""] ?? "미설정"}
          />
          <SummaryRow
            label="비즈니스 유형"
            value={BUSINESS_TYPE_LABELS[company.businessType ?? ""] ?? "미설정"}
          />
          <SummaryRow
            label="주력 제품"
            value={company.mainProduct || "미설정"}
          />
          {company.solutionRequest && (
            <div className="mt-2 rounded-lg bg-white/5 p-3">
              <p className="text-xs leading-relaxed text-slate-400">
                {company.solutionRequest.length > 150
                  ? company.solutionRequest.slice(0, 150) + "..."
                  : company.solutionRequest}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* -- 선택된 프로토타입 -- */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <Cpu className="h-4 w-4 text-emerald-400" aria-hidden="true" />
            솔루션 프로토타입
          </h3>
          <ReSelector stepIndex={1} label="재선택" />
        </div>
        {selectedProto ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-white">
                {selectedProto.name}
              </span>
              <span className="inline-flex items-center rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-300">
                {SOLUTION_TYPE_LABELS[selectedProto.solutionType] ??
                  selectedProto.solutionType}
              </span>
            </div>
            {selectedProto.reasoning && (
              <p className="text-xs leading-relaxed text-slate-400">
                {selectedProto.reasoning.length > 120
                  ? selectedProto.reasoning.slice(0, 120) + "..."
                  : selectedProto.reasoning}
              </p>
            )}
            {/* 아키텍처 프리뷰 썸네일 */}
            <PrototypePreview
              config={selectedProto.config}
              solutionType={selectedProto.solutionType}
            />
          </div>
        ) : (
          <p className="text-xs text-slate-500">선택된 프로토타입 없음</p>
        )}
      </div>

      {/* -- 선택된 PM -- */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <UserCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
            프로젝트 매니저
          </h3>
          <ReSelector stepIndex={2} label="재선택" />
        </div>

        {pmProfile ? (
          <div className="space-y-3">
            {/* PM 미니 카드 */}
            <div className="flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-500/20">
                <UserCircle2 className="h-5 w-5 text-emerald-300" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white">
                  {pmProfile.name}
                </p>
                <div className="mt-0.5 flex flex-wrap items-center gap-2">
                  {(pmProfile.specialties?.[0] ??
                    pmProfile.domain ??
                    pmProfile.title) && (
                    <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-medium text-emerald-400">
                      {pmProfile.specialties?.[0] ??
                        pmProfile.domain ??
                        pmProfile.title}
                    </span>
                  )}
                  {pmProfile.avg_rating > 0 && (
                    <PMRatingStars rating={pmProfile.avg_rating} showValue />
                  )}
                </div>
              </div>
            </div>

            {/* PM 구성 요약 (수량 배지) */}
            {compositionCounts && (
              <div>
                <p className="mb-2 text-[11px] font-medium text-slate-500">
                  PM 구성 요소
                </p>
                <div className="grid grid-cols-5 gap-2">
                  <CompositionCountBadge
                    icon={Bot}
                    label="에이전트"
                    count={compositionCounts.agents}
                    color="text-emerald-400"
                    bg="bg-emerald-500/10"
                  />
                  <CompositionCountBadge
                    icon={Wrench}
                    label="스킬"
                    count={compositionCounts.skills}
                    color="text-sky-400"
                    bg="bg-sky-500/10"
                  />
                  <CompositionCountBadge
                    icon={Webhook}
                    label="훅"
                    count={compositionCounts.hooks}
                    color="text-violet-400"
                    bg="bg-violet-500/10"
                  />
                  <CompositionCountBadge
                    icon={Server}
                    label="MCP"
                    count={compositionCounts.mcp_servers}
                    color="text-amber-400"
                    bg="bg-amber-500/10"
                  />
                  <CompositionCountBadge
                    icon={Puzzle}
                    label="플러그인"
                    count={compositionCounts.plugins}
                    color="text-rose-400"
                    bg="bg-rose-500/10"
                  />
                </div>
              </div>
            )}
          </div>
        ) : pm.selectedPmProfileId ? (
          <p className="text-xs text-slate-400">PM 정보 로딩 중...</p>
        ) : (
          <p className="text-xs text-slate-500">선택된 PM 없음</p>
        )}
      </div>

      {/* -- 최종 안내 -- */}
      <div className="flex flex-col items-center justify-center pt-4 text-center">
        <CheckCircle2
          className="mb-3 h-8 w-8 text-emerald-400"
          aria-hidden="true"
        />
        <p className="text-sm font-medium text-white">
          모든 설정을 확인했습니다
        </p>
        <p className="mt-1 text-xs text-slate-400">
          &ldquo;이대로 진행&rdquo; 버튼을 클릭하면 프로젝트가 생성됩니다
        </p>
      </div>
    </div>
  );
}
