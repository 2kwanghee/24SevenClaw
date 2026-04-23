"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Bot, Info, KeyRound, Link, Sparkles, Wrench } from "lucide-react";
import { useSession } from "next-auth/react";

import { prototypeSessions } from "@/lib/api-client";
import { useCatalogAgents, useCatalogHooks, useCatalogSkills } from "@/hooks/use-catalog";
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
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const agents = useSolutionWizardStore((s) => s.data.agents);
  const setAgents = useSolutionWizardStore((s) => s.setAgents);
  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);

  const [catalogRecommended, setCatalogRecommended] = useState<{ agents: string[]; skills: string[] }>({
    agents: [],
    skills: [],
  });
  const didAutoSelect = useRef(false);

  useEffect(() => {
    if (didAutoSelect.current) return;
    if (!sessionId || !token) return;
    if (agents.selectedAgents.length > 0) return;

    didAutoSelect.current = true;
    prototypeSessions
      .recommendComponents(token, sessionId)
      .then((rec) => {
        if (rec.agents.length > 0 || rec.skills.length > 0) {
          setCatalogRecommended({ agents: rec.agents, skills: rec.skills });
          setAgents({
            ...agents,
            selectedAgents: rec.agents,
            selectedSkills: rec.skills,
          });
        }
      })
      .catch(() => {
        // 실패해도 사용자가 직접 선택 가능
      });
  }, [sessionId, token]); // eslint-disable-line react-hooks/exhaustive-deps

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

  const {
    data: hooksData,
    isLoading: hooksLoading,
    isError: hooksError,
  } = useCatalogHooks();

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

  const toggleHook = (hookId: string) => {
    const selected = (agents.selectedHooks ?? []).includes(hookId)
      ? (agents.selectedHooks ?? []).filter((h) => h !== hookId)
      : [...(agents.selectedHooks ?? []), hookId];
    setAgents({ ...agents, selectedHooks: selected });
  };

  const hasCatalogRecs = catalogRecommended.agents.length > 0 || catalogRecommended.skills.length > 0;

  return (
    <div className="space-y-6">
      {hasCatalogRecs ? (
        <div className="flex items-start gap-2 rounded-xl border border-blue-500/20 bg-blue-500/5 px-4 py-3">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" />
          <p className="text-xs text-slate-400">
            선택한 프로토타입 카탈로그를 기반으로 에이전트와 스킬이 자동 추천되었습니다. 필요에 따라 조정하세요.
          </p>
        </div>
      ) : (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          <p className="text-xs text-slate-400">
            선택한 프로토타입의 에이전트 구성을 확인하고 필요에 따라 조정하세요.
          </p>
        </div>
      )}

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
              const isRecommended = catalogRecommended.agents.includes(id);
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
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`text-sm font-medium ${isSelected ? "text-white" : "text-slate-300"}`}
                    >
                      {label}
                    </span>
                    {isRecommended && (
                      <span className="flex items-center gap-0.5 rounded-full bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-medium text-blue-400">
                        <Sparkles className="h-2.5 w-2.5" />
                        추천
                      </span>
                    )}
                  </div>
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
                {ticketSourceSkills.map(({ id, label, env_vars }) => {
                  const isSelected = agents.selectedSkills.includes(id);
                  const isRecommended = catalogRecommended.skills.includes(id);
                  const needsApiKey = env_vars && env_vars.length > 0;
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => selectTicketSource(id)}
                      aria-pressed={isSelected}
                      className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-all duration-200 ${
                        isSelected
                          ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300 ring-2 ring-emerald-500/20"
                          : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20"
                      }`}
                    >
                      {label}
                      {isRecommended && (
                        <span className="flex items-center gap-0.5 rounded-full bg-blue-500/20 px-1 py-0.5 text-[10px] font-medium text-blue-400">
                          <Sparkles className="h-2.5 w-2.5" />
                        </span>
                      )}
                      {needsApiKey && (
                        <span className="flex items-center gap-0.5 rounded-full border border-amber-500/30 bg-amber-400/10 px-1 py-0.5 text-[10px] font-medium text-amber-400">
                          <KeyRound className="h-2.5 w-2.5" />
                        </span>
                      )}
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
                {otherSkills.map(({ id, label, env_vars }) => {
                  const isSelected = agents.selectedSkills.includes(id);
                  const isRecommended = catalogRecommended.skills.includes(id);
                  const needsApiKey = env_vars && env_vars.length > 0;
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => toggleSkill(id)}
                      aria-pressed={isSelected}
                      className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-all duration-200 ${
                        isSelected
                          ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300 ring-2 ring-emerald-500/20"
                          : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20"
                      }`}
                    >
                      {label}
                      {isRecommended && (
                        <span className="flex items-center gap-0.5 rounded-full bg-blue-500/20 px-1 py-0.5 text-[10px] font-medium text-blue-400">
                          <Sparkles className="h-2.5 w-2.5" />
                        </span>
                      )}
                      {needsApiKey && (
                        <span className="flex items-center gap-0.5 rounded-full border border-amber-500/30 bg-amber-400/10 px-1 py-0.5 text-[10px] font-medium text-amber-400">
                          <KeyRound className="h-2.5 w-2.5" />
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 훅 선택 */}
      {(hooksLoading || hooksError || (hooksData && hooksData.items.length > 0)) && (
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <Link className="h-4 w-4 text-emerald-400" />
            훅 (Hooks)
            <span className="text-[11px] text-slate-500">(선택)</span>
          </label>
          {hooksLoading && <SkillsSkeleton />}
          {hooksError && <FetchError message="훅 목록을 불러오지 못했습니다." />}
          {hooksData && hooksData.items.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {hooksData.items.map(({ id, label, description, event, required }) => {
                const isSelected = (agents.selectedHooks ?? []).includes(id);
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => !required && toggleHook(id)}
                    aria-pressed={isSelected || required}
                    disabled={required}
                    className={`flex flex-col gap-0.5 rounded-xl border px-3 py-2 text-left transition-all duration-200 ${
                      isSelected || required
                        ? "border-purple-500/50 bg-purple-500/10 ring-2 ring-purple-500/20"
                        : "border-white/10 bg-white/5 hover:border-white/20"
                    } ${required ? "cursor-default opacity-80" : ""}`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`text-sm font-medium ${isSelected || required ? "text-white" : "text-slate-300"}`}>
                        {label}
                      </span>
                      {required && (
                        <span className="rounded-full bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose-400">
                          필수
                        </span>
                      )}
                      {event && (
                        <span className="rounded-full bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-slate-400">
                          {event}
                        </span>
                      )}
                    </div>
                    {description && (
                      <span className="text-xs text-slate-500">{description}</span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
