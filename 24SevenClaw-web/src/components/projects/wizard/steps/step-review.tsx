"use client";

import { ClipboardCheck } from "lucide-react";

import { useWizardStore } from "@/stores/wizard-store";

const COMPANY_SIZE_LABELS: Record<string, string> = {
  solo: "1인",
  small: "소규모",
  medium: "중소기업",
  enterprise: "대기업",
};

const INDUSTRY_LABELS: Record<string, string> = {
  it: "IT / 소프트웨어",
  finance: "금융",
  commerce: "커머스",
  healthcare: "헬스케어",
  education: "교육",
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

const PIPELINE_LABELS: Record<string, string> = {
  harness: "하네스 엔지니어링",
  tdd: "TDD Smart Coding",
  "ai-review": "AI 코드 리뷰",
  "telegram-notify": "텔레그램 알림",
  "lint-gate": "린트 Gate",
  "ralph-loop": "Ralph 루프",
};

const PLATFORM_LABELS: Record<string, string> = {
  "claude-code": "Claude Code",
  "gemini-cli": "Gemini CLI",
  codex: "Codex",
  cursor: "Cursor",
};

const STACK_PRESET_LABELS: Record<string, string> = {
  "nextjs-fastapi": "Next.js + FastAPI",
  "react-express": "React + Express",
  "vue-django": "Vue + Django",
  "fastapi-only": "FastAPI Only",
  "nextjs-fullstack": "Next.js Fullstack",
  "spring-react": "Spring + React",
};

export function StepReview() {
  const organization = useWizardStore((s) => s.data.organization);
  const solution = useWizardStore((s) => s.data.solution);
  const agents = useWizardStore((s) => s.data.agents);
  const skills = useWizardStore((s) => s.data.skills);
  const pipelines = useWizardStore((s) => s.data.pipelines);
  const platform = useWizardStore((s) => s.data.platform);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-2 text-sm font-medium text-slate-300">회사 정보</h3>
        <div className="space-y-1.5 text-sm">
          <p className="text-white">
            {organization.companyName || "미설정"}
          </p>
          <p className="text-slate-400">
            {COMPANY_SIZE_LABELS[organization.companySize ?? ""] ?? "미설정"}
            {" · "}
            {INDUSTRY_LABELS[organization.industry ?? ""] ?? "미설정"}
          </p>
          {organization.techStack.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {organization.techStack.map((tech) => (
                <span
                  key={tech}
                  className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-slate-400"
                >
                  {tech}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-2 text-sm font-medium text-slate-300">솔루션</h3>
        <div className="space-y-1.5 text-sm">
          <p className="text-white">
            {solution.projectName || "미설정"}
          </p>
          <p className="text-slate-400">
            {SOLUTION_TYPE_LABELS[solution.solutionType ?? ""] ?? "미설정"}
            {solution.stackPreset && (
              <>
                {" · "}
                {STACK_PRESET_LABELS[solution.stackPreset] ?? solution.stackPreset}
              </>
            )}
          </p>
          {solution.description && (
            <p className="pt-1 text-xs text-slate-500">
              {solution.description}
            </p>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-2 text-sm font-medium text-slate-300">에이전트</h3>
        <p className="text-sm text-slate-500">
          {agents.selectedAgents.length > 0
            ? `${agents.selectedAgents.length}개 선택`
            : "미설정"}
        </p>
      </div>

      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-2 text-sm font-medium text-slate-300">스킬</h3>
        {skills.selectedSkills.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {skills.selectedSkills.map((skill) => (
              <span
                key={skill.id}
                className="inline-flex items-center gap-1 rounded-md bg-white/5 px-2 py-0.5 text-xs text-slate-400"
              >
                {skill.id}
                {skill.apiKey && (
                  <span className="text-emerald-400" title="API 키 설정됨">
                    *
                  </span>
                )}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">미설정</p>
        )}
      </div>

      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-2 text-sm font-medium text-slate-300">파이프라인</h3>
        {pipelines.selectedPipelines.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {pipelines.selectedPipelines.map((id) => (
              <span
                key={id}
                className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-slate-400"
              >
                {PIPELINE_LABELS[id] ?? id}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">미설정</p>
        )}
      </div>

      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="mb-2 text-sm font-medium text-slate-300">플랫폼</h3>
        <p className="text-sm text-slate-500">
          {platform.platformId
            ? PLATFORM_LABELS[platform.platformId] ?? platform.platformId
            : "미설정"}
        </p>
      </div>

      <div className="flex flex-col items-center justify-center pt-4 text-center">
        <ClipboardCheck className="mb-3 h-8 w-8 text-violet-400" />
        <p className="text-sm text-slate-400">
          설정을 확인한 뒤 프로젝트를 생성하세요
        </p>
      </div>
    </div>
  );
}
