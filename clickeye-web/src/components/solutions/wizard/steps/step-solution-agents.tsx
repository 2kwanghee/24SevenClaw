"use client";

import { AlertCircle, Bot, Info, Wrench } from "lucide-react";

import { useCatalogAgents, useCatalogSkills } from "@/hooks/use-catalog";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

function AgentsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-xl border border-white/5 bg-white/[0.02] px-3 py-3"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <div className="h-4 w-24 rounded-md bg-white/[0.07]" />
          <div className="mt-1 h-3 w-32 rounded bg-white/[0.05]" />
        </div>
      ))}
    </div>
  );
}

function SkillsSkeleton() {
  return (
    <div className="flex flex-wrap gap-2" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse h-8 w-20 rounded-lg bg-white/[0.05]"
          style={{ animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  );
}

function FetchError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
      <p className="text-xs text-red-400">{message}</p>
    </div>
  );
}

export function StepSolutionAgents() {
  const agents = useSolutionWizardStore((s) => s.data.agents);
  const setAgents = useSolutionWizardStore((s) => s.setAgents);

  const {
    data: agentsData,
    isLoading: agentsLoading,
    isError: agentsError,
  } = useCatalogAgents();

  const {
    data: skillsData,
    isLoading: skillsLoading,
    isError: skillsError,
  } = useCatalogSkills();

  const ticketSourceSkills = skillsData?.items.filter((s) => s.category === "ticket_source") ?? [];
  const otherSkills = skillsData?.items.filter((s) => s.category !== "ticket_source") ?? [];

  const toggleAgent = (agentId: string) => {
    const selected = agents.selectedAgents.includes(agentId)
      ? agents.selectedAgents.filter((a) => a !== agentId)
      : [...agents.selectedAgents, agentId];
    setAgents({ ...agents, selectedAgents: selected });
  };

  // XOR: 티켓 소스 선택 시 기존 티켓 소스 자동 해제
  const selectTicketSource = (skillId: string) => {
    const ticketSourceIds = ticketSourceSkills.map((s) => s.id);
    const isCurrentlySelected = agents.selectedSkills.includes(skillId);
    const withoutTicketSources = agents.selectedSkills.filter(
      (s) => !ticketSourceIds.includes(s),
    );
    const newSkills = isCurrentlySelected
      ? withoutTicketSources
      : [...withoutTicketSources, skillId];
    setAgents({ ...agents, selectedSkills: newSkills });
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
        {agentsLoading && <AgentsSkeleton />}
        {agentsError && <FetchError message="에이전트 목록을 불러오지 못했습니다." />}
        {agentsData && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {agentsData.items.map(({ id, label, description }) => {
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
                    {label}
                  </span>
                  {description && (
                    <span className="text-xs text-slate-500">{description}</span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* 연동 스킬 */}
      <div className="space-y-4">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
          <Wrench className="h-4 w-4 text-emerald-400" />
          연동 스킬
        </label>

        {/* 티켓 소스 (필수, 1개 선택) */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-300">티켓 소스</span>
            <span className="rounded-full bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose-400">
              필수
            </span>
            <span className="text-[11px] text-slate-500">1개 선택</span>
          </div>
          <p className="text-[11px] text-slate-500">
            이슈/티켓을 관리할 플랫폼을 선택하세요.
          </p>
          {skillsLoading && <SkillsSkeleton />}
          {skillsError && <FetchError message="스킬 목록을 불러오지 못했습니다." />}
          {skillsData && (
            <>
              <div className="flex flex-wrap gap-2">
                {ticketSourceSkills.map(({ id, label }) => {
                  const isSelected = agents.selectedSkills.includes(id);
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => selectTicketSource(id)}
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
              {ticketSourceSkills.length > 0 &&
                !agents.selectedSkills.some((id) =>
                  ticketSourceSkills.some((s) => s.id === id),
                ) && (
                  <p role="alert" className="text-xs text-rose-400">
                    티켓 소스(Linear 또는 Notion)를 1개 선택해야 합니다
                  </p>
                )}
            </>
          )}
        </div>

        {/* 추가 스킬 (선택) */}
        {(skillsLoading || (skillsData && otherSkills.length > 0)) && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-300">추가 스킬</span>
              <span className="text-[11px] text-slate-500">(선택)</span>
            </div>
            {skillsLoading && <SkillsSkeleton />}
            {skillsData && otherSkills.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {otherSkills.map(({ id, label }) => {
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
            )}
          </div>
        )}
      </div>
    </div>
  );
}
