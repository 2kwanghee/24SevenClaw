"use client";

import { ClipboardCheck, Building2, Bot, Terminal, KeyRound, UserCircle2, Cpu } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

const BUSINESS_TYPE_LABELS: Record<string, string> = {
  b2b: "B2B",
  b2c: "B2C",
  b2b2c: "B2B2C",
  internal: "내부 도구",
};

const PLATFORM_LABELS: Record<string, string> = {
  "claude-code": "Claude Code",
  "gemini-cli": "Gemini CLI",
  cursor: "Cursor",
  codex: "Codex",
};

const SOLUTION_TYPE_LABELS: Record<string, string> = {
  saas: "SaaS",
  "rest-api": "REST API",
  fullstack: "풀스택",
  "internal-tool": "내부 도구",
  mvp: "MVP",
  custom: "커스텀",
};

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

export function StepSolutionConfirm() {
  const data = useSolutionWizardStore((s) => s.data);

  const { company, prototypes, pm, agents, platform, env } = data;

  const selectedProto = prototypes.generatedPrototypes.find(
    (p) => p.id === prototypes.selectedPrototypeId,
  );

  const envKeyCount = Object.keys(env.envVars).length;

  return (
    <div className="space-y-4">
      {/* 회사 정보 */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
          <Building2 className="h-4 w-4 text-emerald-400" />
          회사 정보
        </h3>
        <div className="space-y-2">
          <SummaryRow label="회사명" value={company.companyName || "미설정"} />
          <SummaryRow
            label="비즈니스 유형"
            value={
              BUSINESS_TYPE_LABELS[company.businessType ?? ""] ?? "미설정"
            }
          />
          <SummaryRow
            label="주력 제품"
            value={company.mainProduct || "미설정"}
          />
          {company.solutionRequest && (
            <div className="mt-2 rounded-lg bg-white/5 p-3">
              <p className="text-xs leading-relaxed text-slate-400">
                {company.solutionRequest.length > 200
                  ? company.solutionRequest.slice(0, 200) + "..."
                  : company.solutionRequest}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 선택된 프로토타입 */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
          <Cpu className="h-4 w-4 text-emerald-400" />
          솔루션 프로토타입
        </h3>
        {selectedProto ? (
          <div className="space-y-2">
            <SummaryRow label="이름" value={selectedProto.name} />
            <SummaryRow
              label="유형"
              value={
                SOLUTION_TYPE_LABELS[selectedProto.solutionType] ??
                selectedProto.solutionType
              }
            />
          </div>
        ) : (
          <p className="text-xs text-slate-500">선택된 프로토타입 없음</p>
        )}
      </div>

      {/* PM */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
          <UserCircle2 className="h-4 w-4 text-emerald-400" />
          PM
        </h3>
        <p className="text-xs text-slate-400">
          {pm.selectedPmProfileId ? `PM 선택됨 (ID: ${pm.selectedPmProfileId.slice(0, 8)}...)` : "선택된 PM 없음"}
        </p>
      </div>

      {/* 에이전트 & 스킬 */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
          <Bot className="h-4 w-4 text-emerald-400" />
          에이전트 & 스킬
        </h3>
        <div className="space-y-2">
          <SummaryRow
            label="에이전트"
            value={
              agents.selectedAgents.length > 0
                ? `${agents.selectedAgents.join(", ")}`
                : "미설정"
            }
          />
          <SummaryRow
            label="스킬"
            value={
              agents.selectedSkills.length > 0
                ? agents.selectedSkills.join(", ")
                : "없음"
            }
          />
        </div>
      </div>

      {/* 플랫폼 */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
          <Terminal className="h-4 w-4 text-emerald-400" />
          플랫폼
        </h3>
        <p className="text-xs text-slate-400">
          {platform.platformId
            ? PLATFORM_LABELS[platform.platformId] ?? platform.platformId
            : "미설정"}
        </p>
      </div>

      {/* 환경변수 */}
      {envKeyCount > 0 && (
        <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
            <KeyRound className="h-4 w-4 text-emerald-400" />
            환경변수
          </h3>
          <p className="text-xs text-slate-400">{envKeyCount}개 설정됨</p>
        </div>
      )}

      {/* 최종 안내 */}
      <div className="flex flex-col items-center justify-center pt-4 text-center">
        <ClipboardCheck className="mb-3 h-8 w-8 text-emerald-400" />
        <p className="text-sm font-medium text-white">
          모든 설정을 확인했습니다
        </p>
        <p className="mt-1 text-xs text-slate-400">
          프로젝트를 생성하면 솔루션 설정이 저장됩니다
        </p>
      </div>
    </div>
  );
}
