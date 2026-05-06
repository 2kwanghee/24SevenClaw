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
  ShieldCheck,
  KeyRound,
  ExternalLink,
  TrendingDown,
} from "lucide-react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { pmProfiles, type PMProfileWithMetrics } from "@/lib/api-client";
import { PMRatingStars } from "../pm-rating-stars";
import { PrototypePreview } from "../prototype-preview";
import { useCatalogSkills, useCatalogHooks } from "@/hooks/use-catalog";
import { collectEnvVars } from "@/lib/catalog-helpers";

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
      <span className="shrink-0 text-xs text-zinc-500">{label}</span>
      <span className="text-right text-xs text-zinc-700">{value}</span>
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
      className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-zinc-500 transition-colors hover:bg-zinc-50 hover:text-zinc-700"
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
      <span className="text-sm font-semibold text-zinc-950">{count}</span>
      <span className="text-[10px] leading-none text-zinc-500">{label}</span>
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
  osId: string | null;
}

interface StepItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  desc: string;
  command?: string;
  link?: { href: string; label: string };
  note?: string;
}

function SetupGuideModal({ projectId, osId }: SetupGuideModalProps) {
  const isWsl = osId === "wsl2" || osId === null;
  const data = useSolutionWizardStore((s) => s.data);
  const { selectedSkills, selectedHooks } = data.agents;
  const envVars = data.env.envVars;

  const { data: skillsData } = useCatalogSkills();
  const { data: hooksData } = useCatalogHooks();
  const envGroups = collectEnvVars(
    skillsData?.items,
    hooksData?.items,
    selectedSkills,
    selectedHooks ?? [],
  );
  const guideGroups = envGroups.filter((g) => g.vars.length > 0);

  const COMMON_STEPS: StepItem[] = [
    {
      icon: Download,
      label: "ZIP 다운로드",
      desc: '프로젝트 페이지에서 "ZIP 다운로드" 버튼 클릭',
      link: { href: `/projects/${projectId}`, label: "프로젝트 페이지 열기" },
    },
    {
      icon: FolderOpen,
      label: "압축 해제",
      desc: isWsl
        ? "WSL2 Ubuntu 터미널에서 원하는 폴더에 압축 해제합니다"
        : "원하는 폴더에 ZIP 파일을 압축 해제합니다",
      command: isWsl
        ? "unzip <project>.zip -d ~/projects/my-project && cd ~/projects/my-project"
        : "unzip <project>.zip -d my-project && cd my-project",
      ...(isWsl
        ? { note: "Windows 탐색기에서 ZIP 더블클릭 대신 WSL 터미널에서 실행하세요" }
        : {}),
    },
    {
      icon: Terminal,
      label: "런처 스크립트 실행",
      desc: "환경 점검·서비스 기동 후 자동 종료됩니다. 터미널을 닫아도 파이프라인이 계속 실행됩니다.",
      command: "bash start.sh",
    },
    {
      icon: ShieldCheck,
      label: isWsl ? "서비스 영구 등록 (권장)" : "셋업 완료 확인",
      desc: isWsl
        ? "WSL2 종료·재시작 후에도 서비스가 자동 복구됩니다. systemd 사용자 서비스로 등록합니다."
        : "ClickEye 웹 AI Team에서 태스크를 등록하면 로컬 파이프라인이 자동으로 실행됩니다.",
      ...(isWsl ? { command: "bash scripts/install-service.sh" } : {}),
      ...(isWsl ? { note: "선택사항이지만 안정적인 운영을 위해 권장합니다" } : {}),
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div
        className="setup-guide-modal mx-4 flex w-full max-w-2xl flex-col rounded-2xl border border-zinc-200 shadow-2xl"
        style={{ maxHeight: "90vh" }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-modal-title"
      >
        <div className="setup-guide-scroll overflow-y-auto p-6">
          {/* 헤더 */}
          <div className="mb-5 flex flex-col items-center text-center">
            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50">
              <CheckCircle2
                className="h-7 w-7 text-emerald-600"
                aria-hidden="true"
              />
            </div>
            <h2
              id="guide-modal-title"
              className="text-lg font-bold text-zinc-950"
            >
              솔루션이 생성되었습니다!
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              아래 절차로 로컬 개발 환경을 셋업하세요
            </p>
          </div>

          {/* 공통 단계별 가이드 */}
          <ol className="mb-5 space-y-3" aria-label="셋업 절차">
            {COMMON_STEPS.map((step, i) => {
              const Icon = step.icon;
              return (
                <li key={step.label} className="flex items-start gap-3">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-xs font-bold text-emerald-600">
                    {i + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <Icon
                        className="h-3.5 w-3.5 shrink-0 text-emerald-600"
                        aria-hidden="true"
                      />
                      <span className="text-sm font-medium text-zinc-700">
                        {step.label}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-zinc-500">{step.desc}</p>
                    {step.command && (
                      <code className="setup-guide-modal-code mt-1.5 block rounded-lg px-2.5 py-1.5 font-mono text-[11px] text-emerald-600">
                        {step.command}
                      </code>
                    )}
                    {step.note && (
                      <p className="mt-1 text-[11px] text-amber-400/80">
                        {step.note}
                      </p>
                    )}
                    {step.link && (
                      <Link
                        href={step.link.href}
                        className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-sky-400 transition-colors hover:text-sky-300"
                      >
                        <ExternalLink className="h-2.5 w-2.5" aria-hidden="true" />
                        {step.link.label}
                      </Link>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>

          {/* 연동 설정 가이드 (선택 자산별 동적 렌더링) */}
          {guideGroups.length > 0 && (
            <div className="mb-5 space-y-3">
              <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                연동 설정 가이드
              </p>
              {guideGroups.map((group) => (
                <div
                  key={group.skillId}
                  className="rounded-xl border border-zinc-200 bg-zinc-50 p-3"
                >
                  <div className="mb-2 flex items-center gap-1.5">
                    <KeyRound
                      className="h-3 w-3 text-amber-400"
                      aria-hidden="true"
                    />
                    <span className="text-xs font-semibold text-zinc-700">
                      {group.skillLabel}
                    </span>
                  </div>
                  <div className="mb-2 flex flex-wrap gap-1.5">
                    {group.vars.map((v) => {
                      const filled = !!envVars[v.name]?.trim();
                      return (
                        <span
                          key={v.name}
                          className={cn(
                            "flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-mono text-[10px]",
                            filled
                              ? "bg-emerald-50 text-emerald-600"
                              : "bg-zinc-50 text-zinc-500",
                          )}
                        >
                          {filled ? (
                            <CheckCircle2
                              className="h-2.5 w-2.5"
                              aria-hidden="true"
                            />
                          ) : (
                            <span className="inline-block h-2.5 w-2.5 rounded-full border border-zinc-300" />
                          )}
                          {v.name}
                        </span>
                      );
                    })}
                  </div>
                  {group.bodyMd && (
                    <div className="prose prose-xs prose-invert max-w-none text-[11px] text-zinc-500 [&_a]:text-sky-400 [&_code]:rounded [&_code]:bg-zinc-50 [&_code]:px-1 [&_code]:text-emerald-600 [&_h1]:text-xs [&_h2]:text-xs [&_h3]:text-xs [&_li]:mb-0.5 [&_ol]:pl-4 [&_p]:mb-1 [&_ul]:pl-4">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {group.bodyMd}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 셋업 완료 후 워크플로 */}
          <div className="mb-5 space-y-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
            <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              셋업 완료 후 워크플로
            </p>
            <div className="space-y-1 text-[11px] text-zinc-500">
              <p>
                ①{" "}
                <code className="text-emerald-600">bash start.sh</code> → 환경
                점검·서비스 백그라운드 기동 후 자동 종료
              </p>
              {isWsl && (
                <p>
                  ②{" "}
                  <code className="text-emerald-600">
                    bash scripts/install-service.sh
                  </code>{" "}
                  → systemd 서비스 등록 (WSL2 재시작 후 자동 복구)
                </p>
              )}
              <p>
                {isWsl ? "③" : "②"} ClickEye 웹 → AI Team → 태스크 승인
                (Todo)
              </p>
              <p>
                {isWsl ? "④" : "③"} 로컬 파이프라인이 자동으로 Claude를
                호출해 코드를 작성합니다
              </p>
            </div>
            <p className="mt-2 border-t border-emerald-100 pt-2 text-[11px] text-zinc-500">
              팀 공유용 슬라이드 가이드: ZIP 내{" "}
              <code className="text-zinc-500">docs/setup-guide.pptx</code>
            </p>
          </div>

          {/* 액션 버튼 */}
          <Link
            href={`/projects/${projectId}`}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-zinc-900/10 transition-colors hover:bg-zinc-800"
          >
            프로젝트 페이지로 이동
          </Link>
          <p className="mt-2 text-center text-[11px] text-zinc-500">
            프로젝트 페이지에서 ZIP 다운로드 및 연동 상태를 확인할 수 있습니다
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
  const { company, prototypes, pm, roi } = data;

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
    return (
      <SetupGuideModal
        projectId={createdProjectId}
        osId={data.os.osId}
      />
    );
  }

  return (
    <div className="space-y-4" role="region" aria-label="최종 확인">
      {/* -- 회사 정보 -- */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-700">
            <Building2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
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
            <div className="mt-2 rounded-lg bg-zinc-50 p-3">
              <p className="text-xs leading-relaxed text-zinc-500">
                {company.solutionRequest.length > 150
                  ? company.solutionRequest.slice(0, 150) + "..."
                  : company.solutionRequest}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* -- 선택된 프로토타입 -- */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-700">
            <Cpu className="h-4 w-4 text-emerald-600" aria-hidden="true" />
            솔루션 프로토타입
          </h3>
          <ReSelector stepIndex={1} label="재선택" />
        </div>
        {selectedProto ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-zinc-950">
                {selectedProto.name}
              </span>
              <span className="inline-flex items-center rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600">
                {SOLUTION_TYPE_LABELS[selectedProto.solutionType] ??
                  selectedProto.solutionType}
              </span>
            </div>
            {selectedProto.reasoning && (
              <p className="text-xs leading-relaxed text-zinc-500">
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
          <p className="text-xs text-zinc-500">선택된 프로토타입 없음</p>
        )}
      </div>

      {/* -- 선택된 PM -- */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-700">
            <UserCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
            프로젝트 매니저
          </h3>
          <ReSelector stepIndex={2} label="재선택" />
        </div>

        {pmProfile ? (
          <div className="space-y-3">
            {/* PM 미니 카드 */}
            <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100">
                <UserCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-zinc-950">
                  {pmProfile.name}
                </p>
                <div className="mt-0.5 flex flex-wrap items-center gap-2">
                  {(pmProfile.specialties?.[0] ??
                    pmProfile.domain ??
                    pmProfile.title) && (
                    <span className="inline-flex items-center rounded-md bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-600">
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
                <p className="mb-2 text-[11px] font-medium text-zinc-500">
                  PM 구성 요소
                </p>
                <div className="grid grid-cols-5 gap-2">
                  <CompositionCountBadge
                    icon={Bot}
                    label="에이전트"
                    count={compositionCounts.agents}
                    color="text-emerald-600"
                    bg="bg-emerald-50"
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
          <p className="text-xs text-zinc-500">PM 정보 로딩 중...</p>
        ) : (
          <p className="text-xs text-zinc-500">선택된 PM 없음</p>
        )}
      </div>

      {/* -- ROI 요약 -- */}
      {roi.result && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-medium text-emerald-700">
              <TrendingDown className="h-4 w-4" aria-hidden="true" />
              ROI 비교 요약
            </h3>
            <ReSelector stepIndex={10} label="재계산" />
          </div>
          <div className="space-y-2">
            <SummaryRow
              label="기존 인력 비용"
              value={new Intl.NumberFormat("ko-KR", { style: "currency", currency: "KRW", maximumFractionDigits: 0 }).format(roi.result.baselineCost)}
            />
            <SummaryRow
              label="ClickEye 도입 비용"
              value={new Intl.NumberFormat("ko-KR", { style: "currency", currency: "KRW", maximumFractionDigits: 0 }).format(roi.result.clickeyeCost)}
            />
            <SummaryRow
              label="예상 절감액"
              value={new Intl.NumberFormat("ko-KR", { style: "currency", currency: "KRW", maximumFractionDigits: 0 }).format(roi.result.savings)}
            />
            <SummaryRow
              label="절감률"
              value={`${Math.round(roi.result.savingsRatio * 100)}%`}
            />
          </div>
          <p className="mt-3 text-[10px] text-emerald-600/70">공식 버전: {roi.result.formulaVersion}</p>
        </div>
      )}

      {/* -- 최종 안내 -- */}
      <div className="flex flex-col items-center justify-center pt-4 text-center">
        <CheckCircle2
          className="mb-3 h-8 w-8 text-emerald-600"
          aria-hidden="true"
        />
        <p className="text-sm font-medium text-zinc-950">
          모든 설정을 확인했습니다
        </p>
        <p className="mt-1 text-xs text-zinc-500">
          &ldquo;이대로 진행&rdquo; 버튼을 클릭하면 프로젝트가 생성됩니다
        </p>
      </div>
    </div>
  );
}
