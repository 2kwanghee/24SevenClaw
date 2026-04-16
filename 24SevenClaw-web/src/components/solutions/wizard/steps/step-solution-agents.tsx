"use client";

import { Bot, Wrench, Info } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

const AGENT_LABELS: Record<string, { label: string; description: string }> = {
  harness: { label: "Harness", description: "코드 품질 게이트" },
  architect: { label: "Architect", description: "시스템 설계" },
  frontend: { label: "Frontend", description: "UI/UX 구현" },
  backend: { label: "Backend", description: "API/서버" },
  qa: { label: "QA", description: "테스트 자동화" },
  devops: { label: "DevOps", description: "인프라/배포" },
  security: { label: "Security", description: "보안 감사" },
};

const SKILL_LABELS: Record<string, string> = {
  linear: "Linear",
  telegram: "Telegram",
  github: "GitHub",
  slack: "Slack",
  jira: "Jira",
  notion: "Notion",
};

export function StepSolutionAgents() {
  const agents = useSolutionWizardStore((s) => s.data.agents);
  const setAgents = useSolutionWizardStore((s) => s.setAgents);

  const toggleAgent = (agentId: string) => {
    const selected = agents.selectedAgents.includes(agentId)
      ? agents.selectedAgents.filter((a) => a !== agentId)
      : [...agents.selectedAgents, agentId];
    setAgents({ ...agents, selectedAgents: selected });
  };

  const toggleSkill = (skillId: string) => {
    const selected = agents.selectedSkills.includes(skillId)
      ? agents.selectedSkills.filter((s) => s !== skillId)
      : [...agents.selectedSkills, skillId];
    setAgents({ ...agents, selectedSkills: selected });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
        <p className="text-xs text-slate-400">
          선택한 프로토타입의 에이전트 구성을 확인하고 필요에 따라 조정하세요.
        </p>
      </div>

      {/* 에이전트 선택 */}
      <div className="space-y-3">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
          <Bot className="h-4 w-4 text-emerald-400" />
          AI 에이전트
        </label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(AGENT_LABELS).map(([id, meta]) => {
            const isSelected = agents.selectedAgents.includes(id);
            return (
              <button
                key={id}
                type="button"
                onClick={() => toggleAgent(id)}
                aria-pressed={isSelected}
                className={`flex flex-col gap-0.5 rounded-xl border px-3 py-3 text-left transition-all duration-200 ${
                  isSelected
                    ? "border-emerald-500/50 bg-emerald-500/10 ring-2 ring-emerald-500/20"
                    : "border-white/10 bg-white/5 hover:border-white/20"
                }`}
              >
                <span
                  className={`text-sm font-medium ${isSelected ? "text-white" : "text-slate-300"}`}
                >
                  {meta.label}
                </span>
                <span className="text-xs text-slate-500">{meta.description}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 스킬 선택 */}
      <div className="space-y-3">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
          <Wrench className="h-4 w-4 text-emerald-400" />
          연동 스킬{" "}
          <span className="text-xs font-normal text-slate-500">(선택)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {Object.entries(SKILL_LABELS).map(([id, label]) => {
            const isSelected = agents.selectedSkills.includes(id);
            return (
              <button
                key={id}
                type="button"
                onClick={() => toggleSkill(id)}
                aria-pressed={isSelected}
                className={`rounded-lg border px-3 py-1.5 text-sm transition-all duration-200 ${
                  isSelected
                    ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300 ring-2 ring-emerald-500/20"
                    : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
