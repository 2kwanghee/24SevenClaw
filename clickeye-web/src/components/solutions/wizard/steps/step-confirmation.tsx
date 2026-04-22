"use client";

import React, { useEffect, useState } from "react";
import type { ComponentType } from "react";
import Link from "next/link";
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
  Download,
  Terminal,
  FolderOpen,
  Sparkles,
  Globe,
  KeyRound,
  ExternalLink,
  Zap,
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

/* ---------------------------------------------------------------------------
  SetupGuideModal — 프로젝트 생성 완료 후 /ClickEyeStart 온보딩 가이드
--------------------------------------------------------------------------- */

interface SetupGuideModalProps {
  projectId: string;
  hasLinear: boolean;
}

interface StepItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  desc: string;
  command?: string;
  link?: { href: string; label: string };
}

function SetupGuideModal({ projectId, hasLinear }: SetupGuideModalProps) {
  const SIMPLE_STEPS: StepItem[] = [
    {
      icon: Download,
      label: "ZIP 다운로드",
      desc: '프로젝트 페이지에서 "ZIP 다운로드" 버튼 클릭',
    },
    {
      icon: FolderOpen,
      label: "압축 해제",
      desc: "원하는 폴더에 ZIP 파일을 압축 해제합니다",
    },
    {
      icon: Terminal,
      label: "Claude Code 실행",
      desc: "압축 해제한 폴더에서 터미널을 열고 claude 실행",
    },
    {
      icon: Sparkles,
      label: "/ClickEyeStart 실행",
      desc: "Claude Code에서 /ClickEyeStart 커맨드를 입력하면 자동 셋업이 시작됩니다",
    },
  ];

  const LINEAR_STEPS: StepItem[] = [
    {
      icon: Download,
      label: "ZIP 다운로드",
      desc: '프로젝트 페이지에서 "ZIP 다운로드" 버튼 클릭',
      link: { href: `/projects/${projectId}`, label: "프로젝트 페이지 열기" },
    },
    {
      icon: FolderOpen,
      label: "압축 해제",
      desc: "원하는 폴더에 ZIP 파일을 압축 해제합니다",
    },
    {
      icon: KeyRound,
      label: ".env 작성",
      desc: "ANTHROPIC_API_KEY · LINEAR_API_KEY · LINEAR_TEAM_ID · WEBHOOK_SECRET 설정",
      command: "cp .env.example .env",
    },
    {
      icon: Globe,
      label: "터널 생성",
      desc: "Cloudflare 터널을 기동해 외부 접속 URL을 발급받습니다",
      command: "bash scripts/setup-tunnel.sh",
    },
    {
      icon: ExternalLink,
      label: "Linear 연동 등록",
      desc: "발급된 터널 URL을 ClickEye에 저장하면 Linear webhook이 자동 등록됩니다",
      link: { href: "/settings/linear", label: "Linear 설정 열기" },
    },
    {
      icon: Server,
      label: "Webhook 서버 기동",
      desc: "로컬 포트 9876에서 Linear 이벤트 수신을 시작합니다",
      command: "bash scripts/start-webhook.sh",
    },
    {
      icon: Terminal,
      label: "Claude Code 실행",
      desc: "ZIP 폴더에서 터미널을 열고 claude → /ClickEyeStart 실행",
    },
    {
      icon: Sparkles,
      label: "AI Team 초안 생성",
      desc: '"새 작업 요청" → "AI 초안 생성" 클릭 → Linear에 이슈가 자동 등록됩니다',
      link: {
        href: `/projects/${projectId}/ai-team`,
        label: "AI Team 열기",
      },
    },
    {
      icon: Zap,
      label: "Linear 이슈 → Queued",
      desc: '이슈 상태를 "Queued"로 변경하면 로컬 Claude가 자동으로 작업을 시작합니다',
    },
  ];

  const STEPS = hasLinear ? LINEAR_STEPS : SIMPLE_STEPS;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div
        className="mx-4 flex w-full max-w-md flex-col rounded-2xl border border-emerald-500/20 bg-slate-900 shadow-2xl"
        style={{ maxHeight: "90vh" }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-modal-title"
      >
        <div className="overflow-y-auto p-6">
          {/* 헤더 */}
          <div className="mb-5 flex flex-col items-center text-center">
            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/15">
              <CheckCircle2
                className="h-7 w-7 text-emerald-400"
                aria-hidden="true"
              />
            </div>
            <h2
              id="guide-modal-title"
              className="text-lg font-bold text-white"
            >
              솔루션이 생성되었습니다!
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {hasLinear
                ? "아래 절차로 AI Team → Linear → Claude 자동화를 완성하세요"
                : "아래 절차로 로컬 개발 환경을 셋업하세요"}
            </p>
          </div>

          {/* 단계별 가이드 */}
          <ol className="mb-5 space-y-3" aria-label="셋업 절차">
            {STEPS.map(({ icon: Icon, label, desc, command, link }, i) => (
              <li key={label} className="flex items-start gap-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-xs font-bold text-emerald-400">
                  {i + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <Icon
                      className="h-3.5 w-3.5 shrink-0 text-emerald-400"
                      aria-hidden="true"
                    />
                    <span className="text-sm font-medium text-slate-200">
                      {label}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">{desc}</p>
                  {command && (
                    <code className="mt-1.5 block rounded-lg bg-black/40 px-2.5 py-1.5 font-mono text-[11px] text-emerald-300">
                      {command}
                    </code>
                  )}
                  {link && (
                    <Link
                      href={link.href}
                      className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-sky-400 transition-colors hover:text-sky-300"
                    >
                      <ExternalLink className="h-2.5 w-2.5" aria-hidden="true" />
                      {link.label}
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ol>

          {/* 커맨드 강조 (단순 경로만) */}
          {!hasLinear && (
            <div className="mb-5 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
              <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-500">
                Claude Code에서 실행
              </p>
              <code className="text-sm font-semibold text-emerald-300">
                /ClickEyeStart
              </code>
              <p className="mt-1 text-[11px] text-slate-500">
                API 키 자동 검증 + 누락 키 대화형 입력 안내
              </p>
            </div>
          )}

          {/* 액션 버튼 */}
          <Link
            href={`/projects/${projectId}`}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-600/25 transition-colors hover:bg-emerald-500"
          >
            프로젝트 페이지로 이동
          </Link>
          <p className="mt-2 text-center text-[11px] text-slate-600">
            프로젝트 페이지에서 ZIP 다운로드 및 Linear 연동 상태를 확인할 수 있습니다
          </p>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
  StepConfirmation
--------------------------------------------------------------------------- */

export function StepConfirmation() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const createdProjectId = useSolutionWizardStore((s) => s.createdProjectId);
  const data = useSolutionWizardStore((s) => s.data);
  const { company, prototypes, pm } = data;
  const hasLinear = data.agents.selectedSkills.includes("linear");

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

  if (createdProjectId) {
    return <SetupGuideModal projectId={createdProjectId} hasLinear={hasLinear} />;
  }

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
