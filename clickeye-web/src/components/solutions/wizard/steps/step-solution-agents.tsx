"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Bot, Info, KeyRound, Link, Lock, Server, Sparkles, Wrench } from "lucide-react";
import { useSession } from "next-auth/react";

import { pmProfiles, prototypeSessions } from "@/lib/api-client";
import { useCatalogAgents, useCatalogHooks, useCatalogMCPs, useCatalogSkills } from "@/hooks/use-catalog";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

/* ---------- 스켈레톤 / 에러 ---------- */

function AgentsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-3"
          style={{ animationDelay: `${i * 80}ms` }}
        >
          <div className="h-4 w-24 rounded-md bg-zinc-100" />
          <div className="mt-1 h-3 w-32 rounded bg-zinc-100" />
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
          className="animate-pulse h-8 w-20 rounded-lg bg-zinc-100"
          style={{ animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  );
}

function FetchError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
      <p className="text-xs text-red-600">{message}</p>
    </div>
  );
}

/* ---------- PM 잠금 배지 ---------- */

function PmLockBadge({ pmName }: { pmName?: string }) {
  return (
    <span
      title={pmName ? `${pmName} PM의 기본 팀 항목` : "PM 기본 팀 항목 — 해제 불가"}
      className="flex items-center gap-0.5 rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-600"
    >
      <Lock className="h-2.5 w-2.5" />
      PM 팀
    </span>
  );
}

/* ---------- PM 잠금 슬러그 집합 ---------- */

interface PmLockedSlugs {
  agents: Set<string>;
  skills: Set<string>;
  hooks: Set<string>;
  mcps: Set<string>;
}

export function StepSolutionAgents() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const agents = useSolutionWizardStore((s) => s.data.agents);
  const setAgents = useSolutionWizardStore((s) => s.setAgents);
  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);
  const selectedPmProfileId = useSolutionWizardStore((s) => s.data.pm.selectedPmProfileId);
  const recommendedItems = useSolutionWizardStore((s) => s.data.pm.recommendedItems);

  const selectedPMInfo = recommendedItems.find((i) => i.pmId === selectedPmProfileId);

  const [pmLocked, setPmLocked] = useState<PmLockedSlugs>({
    agents: new Set(),
    skills: new Set(),
    hooks: new Set(),
    mcps: new Set(),
  });

  const [catalogRecommended, setCatalogRecommended] = useState<{ agents: string[]; skills: string[] }>({
    agents: [],
    skills: [],
  });

  const didPmLoad = useRef(false);
  const didAutoSelect = useRef(false);

  /* -- PM composition 자동 적용 -- */
  useEffect(() => {
    if (didPmLoad.current) return;
    if (!selectedPmProfileId || !token) return;

    didPmLoad.current = true;

    pmProfiles
      .getComposition(token, selectedPmProfileId)
      .then((comp) => {
        const lockedAgents = new Set(comp.agents.map((c) => c.component_slug));
        const lockedSkills = new Set(comp.skills.map((c) => c.component_slug));
        const lockedHooks = new Set(comp.hooks.map((c) => c.component_slug));
        const lockedMcps = new Set(comp.mcp_servers.map((c) => c.component_slug));

        setPmLocked({ agents: lockedAgents, skills: lockedSkills, hooks: lockedHooks, mcps: lockedMcps });

        // PM 잠금 항목을 현재 선택에 강제 추가 (이미 있으면 덮어쓰지 않고 병합)
        setAgents({
          selectedAgents: [...new Set([...agents.selectedAgents, ...lockedAgents])],
          selectedSkills: [...new Set([...agents.selectedSkills, ...lockedSkills])],
          selectedHooks: [...new Set([...(agents.selectedHooks ?? []), ...lockedHooks])],
          selectedMcps: [...new Set([...(agents.selectedMcps ?? []), ...lockedMcps])],
        });
      })
      .catch(() => {
        // PM 구성 로드 실패 시 기존 추천 로직으로 폴백
      });
  }, [selectedPmProfileId, token]); // eslint-disable-line react-hooks/exhaustive-deps

  /* -- 프로토타입 기반 자동 추천 (PM 없을 때 또는 추가 추천) -- */
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
            selectedAgents: [...new Set([...agents.selectedAgents, ...rec.agents])],
            selectedSkills: [...new Set([...agents.selectedSkills, ...rec.skills])],
          });
        }
      })
      .catch(() => {});
  }, [sessionId, token]); // eslint-disable-line react-hooks/exhaustive-deps

  /* -- 카탈로그 훅 -- */
  const { data: agentsData, isLoading: agentsLoading, isError: agentsError } = useCatalogAgents();
  const { data: skillsData, isLoading: skillsLoading, isError: skillsError } = useCatalogSkills();
  const { data: hooksData, isLoading: hooksLoading, isError: hooksError } = useCatalogHooks();
  const { data: mcpsData, isLoading: mcpsLoading, isError: mcpsError } = useCatalogMCPs();

  const ticketSourceSkills = skillsData?.items.filter((s) => s.category === "ticket_source") ?? [];
  const otherSkills = skillsData?.items.filter((s) => s.category !== "ticket_source") ?? [];

  /* -- 토글 핸들러 (잠금 항목 보호) -- */
  const toggleAgent = (agentId: string) => {
    if (pmLocked.agents.has(agentId)) return;
    const selected = agents.selectedAgents.includes(agentId)
      ? agents.selectedAgents.filter((a) => a !== agentId)
      : [...agents.selectedAgents, agentId];
    setAgents({ ...agents, selectedAgents: selected });
  };

  const selectTicketSource = (skillId: string) => {
    if (pmLocked.skills.has(skillId)) return;
    const ticketSourceIds = ticketSourceSkills.map((s) => s.id);
    const isCurrentlySelected = agents.selectedSkills.includes(skillId);
    // 잠금 티켓소스는 제거하지 않음
    const withoutFreeTicketSources = agents.selectedSkills.filter(
      (s) => !ticketSourceIds.includes(s) || pmLocked.skills.has(s),
    );
    const newSkills = isCurrentlySelected
      ? withoutFreeTicketSources
      : [...withoutFreeTicketSources, skillId];
    setAgents({ ...agents, selectedSkills: newSkills });
  };

  const toggleSkill = (skillId: string) => {
    if (pmLocked.skills.has(skillId)) return;
    const selected = agents.selectedSkills.includes(skillId)
      ? agents.selectedSkills.filter((s) => s !== skillId)
      : [...agents.selectedSkills, skillId];
    setAgents({ ...agents, selectedSkills: selected });
  };

  const toggleHook = (hookId: string) => {
    if (pmLocked.hooks.has(hookId)) return;
    const current = agents.selectedHooks ?? [];
    const selected = current.includes(hookId)
      ? current.filter((h) => h !== hookId)
      : [...current, hookId];
    setAgents({ ...agents, selectedHooks: selected });
  };

  const toggleMcp = (mcpId: string) => {
    if (pmLocked.mcps.has(mcpId)) return;
    const current = agents.selectedMcps ?? [];
    const selected = current.includes(mcpId)
      ? current.filter((m) => m !== mcpId)
      : [...current, mcpId];
    setAgents({ ...agents, selectedMcps: selected });
  };

  const hasPmLock = pmLocked.agents.size + pmLocked.skills.size + pmLocked.hooks.size + pmLocked.mcps.size > 0;
  const hasCatalogRecs = catalogRecommended.agents.length > 0 || catalogRecommended.skills.length > 0;

  return (
    <div className="space-y-6">
      {/* 상단 안내 배너 */}
      {hasPmLock ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <Lock className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
          <p className="text-xs text-zinc-600">
            <span className="font-medium text-zinc-800">{selectedPMInfo?.name ?? "선택한 PM"}</span>의 기본 팀 항목이 자동으로 적용되었습니다.
            잠금 항목은 해제할 수 없으며, 추가 항목은 자유롭게 선택하세요.
          </p>
        </div>
      ) : hasCatalogRecs ? (
        <div className="flex items-start gap-2 rounded-xl border border-blue-500/20 bg-blue-500/5 px-4 py-3">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" />
          <p className="text-xs text-zinc-500">
            선택한 프로토타입 카탈로그를 기반으로 에이전트와 스킬이 자동 추천되었습니다. 필요에 따라 조정하세요.
          </p>
        </div>
      ) : (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
          <p className="text-xs text-zinc-500">
            선택한 프로토타입의 에이전트 구성을 확인하고 필요에 따라 조정하세요.
          </p>
        </div>
      )}

      {/* 에이전트 선택 */}
      <div className="space-y-3">
        <label className="flex items-center gap-2 text-sm font-medium text-zinc-700">
          <Bot className="h-4 w-4 text-emerald-600" />
          AI 에이전트
        </label>
        {agentsLoading && <AgentsSkeleton />}
        {agentsError && <FetchError message="에이전트 목록을 불러오지 못했습니다." />}
        {agentsData && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {agentsData.items.map(({ id, label, description }) => {
              const isSelected = agents.selectedAgents.includes(id);
              const isLocked = pmLocked.agents.has(id);
              const isRecommended = catalogRecommended.agents.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => toggleAgent(id)}
                  aria-pressed={isSelected}
                  disabled={isLocked}
                  className={`flex flex-col gap-0.5 rounded-xl border px-3 py-3 text-left transition-all duration-200 ${
                    isLocked
                      ? "cursor-default border-amber-300/60 bg-amber-50/60 ring-1 ring-amber-300/40"
                      : isSelected
                        ? "border-zinc-900 bg-zinc-50 ring-2 ring-zinc-900/10"
                        : "border-zinc-200 bg-zinc-50 hover:border-zinc-300"
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    <span className={`text-sm font-medium ${isSelected || isLocked ? "text-zinc-950" : "text-zinc-700"}`}>
                      {label}
                    </span>
                    {isLocked && <PmLockBadge pmName={selectedPMInfo?.name} />}
                    {!isLocked && isRecommended && (
                      <span className="flex items-center gap-0.5 rounded-full bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-medium text-blue-400">
                        <Sparkles className="h-2.5 w-2.5" />
                        추천
                      </span>
                    )}
                  </div>
                  {description && <span className="text-xs text-zinc-500">{description}</span>}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* 연동 스킬 */}
      <div className="space-y-4">
        <label className="flex items-center gap-2 text-sm font-medium text-zinc-700">
          <Wrench className="h-4 w-4 text-emerald-600" />
          연동 스킬
        </label>

        {/* 티켓 소스 (필수, 1개 선택) */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-zinc-700">티켓 소스</span>
            <span className="rounded-full bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose-400">필수</span>
            <span className="text-[11px] text-zinc-500">1개 선택</span>
          </div>
          <p className="text-[11px] text-zinc-500">이슈/티켓을 관리할 플랫폼을 선택하세요.</p>
          {skillsLoading && <SkillsSkeleton />}
          {skillsError && <FetchError message="스킬 목록을 불러오지 못했습니다." />}
          {skillsData && (
            <>
              <div className="flex flex-wrap gap-2">
                {ticketSourceSkills.map(({ id, label, env_vars }) => {
                  const isSelected = agents.selectedSkills.includes(id);
                  const isLocked = pmLocked.skills.has(id);
                  const isRecommended = catalogRecommended.skills.includes(id);
                  const needsApiKey = env_vars && env_vars.length > 0;
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => selectTicketSource(id)}
                      aria-pressed={isSelected}
                      disabled={isLocked}
                      className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-all duration-200 ${
                        isLocked
                          ? "cursor-default border-amber-300/60 bg-amber-50 text-zinc-800"
                          : isSelected
                            ? "border-zinc-900 bg-zinc-50 text-zinc-900 ring-2 ring-zinc-900/10"
                            : "border-zinc-200 bg-zinc-50 text-zinc-500 hover:border-zinc-300"
                      }`}
                    >
                      {label}
                      {isLocked && <PmLockBadge pmName={selectedPMInfo?.name} />}
                      {!isLocked && isRecommended && (
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
                !agents.selectedSkills.some((id) => ticketSourceSkills.some((s) => s.id === id)) && (
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
              <span className="text-xs font-medium text-zinc-700">추가 스킬</span>
              <span className="text-[11px] text-zinc-500">(선택)</span>
            </div>
            {skillsLoading && <SkillsSkeleton />}
            {skillsData && otherSkills.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {otherSkills.map(({ id, label, env_vars }) => {
                  const isSelected = agents.selectedSkills.includes(id);
                  const isLocked = pmLocked.skills.has(id);
                  const isRecommended = catalogRecommended.skills.includes(id);
                  const needsApiKey = env_vars && env_vars.length > 0;
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => toggleSkill(id)}
                      aria-pressed={isSelected}
                      disabled={isLocked}
                      className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-all duration-200 ${
                        isLocked
                          ? "cursor-default border-amber-300/60 bg-amber-50 text-zinc-800"
                          : isSelected
                            ? "border-zinc-900 bg-zinc-50 text-zinc-900 ring-2 ring-zinc-900/10"
                            : "border-zinc-200 bg-zinc-50 text-zinc-500 hover:border-zinc-300"
                      }`}
                    >
                      {label}
                      {isLocked && <PmLockBadge pmName={selectedPMInfo?.name} />}
                      {!isLocked && isRecommended && (
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

      {/* MCP 서버 선택 (신규) */}
      {(mcpsLoading || mcpsError || (mcpsData && mcpsData.items.length > 0)) && (
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-zinc-700">
            <Server className="h-4 w-4 text-emerald-600" />
            MCP 서버
            <span className="text-[11px] text-zinc-500">(선택)</span>
          </label>
          {mcpsLoading && <SkillsSkeleton />}
          {mcpsError && <FetchError message="MCP 목록을 불러오지 못했습니다." />}
          {mcpsData && mcpsData.items.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {mcpsData.items.map(({ id, label, description, category }) => {
                const isSelected = (agents.selectedMcps ?? []).includes(id);
                const isLocked = pmLocked.mcps.has(id);
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => toggleMcp(id)}
                    aria-pressed={isSelected}
                    disabled={isLocked}
                    className={`flex flex-col gap-0.5 rounded-xl border px-3 py-2 text-left transition-all duration-200 ${
                      isLocked
                        ? "cursor-default border-amber-300/60 bg-amber-50/60 ring-1 ring-amber-300/40"
                        : isSelected
                          ? "border-zinc-900 bg-zinc-50 ring-2 ring-zinc-900/10"
                          : "border-zinc-200 bg-zinc-50 hover:border-zinc-300"
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`text-sm font-medium ${isSelected || isLocked ? "text-zinc-950" : "text-zinc-700"}`}>
                        {label}
                      </span>
                      {isLocked && <PmLockBadge pmName={selectedPMInfo?.name} />}
                      {category && (
                        <span className="rounded-full bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-zinc-500">
                          {category}
                        </span>
                      )}
                    </div>
                    {description && <span className="text-xs text-zinc-500">{description}</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 훅 선택 */}
      {(hooksLoading || hooksError || (hooksData && hooksData.items.length > 0)) && (
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-zinc-700">
            <Link className="h-4 w-4 text-emerald-600" />
            훅 (Hooks)
            <span className="text-[11px] text-zinc-500">(선택)</span>
          </label>
          {hooksLoading && <SkillsSkeleton />}
          {hooksError && <FetchError message="훅 목록을 불러오지 못했습니다." />}
          {hooksData && hooksData.items.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {hooksData.items.map(({ id, label, description, event, required }) => {
                const isSelected = (agents.selectedHooks ?? []).includes(id);
                const isLocked = pmLocked.hooks.has(id);
                const effectiveDisabled = required || isLocked;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => !effectiveDisabled && toggleHook(id)}
                    aria-pressed={isSelected || required}
                    disabled={effectiveDisabled}
                    className={`flex flex-col gap-0.5 rounded-xl border px-3 py-2 text-left transition-all duration-200 ${
                      isLocked
                        ? "cursor-default border-amber-300/60 bg-amber-50/60 ring-1 ring-amber-300/40"
                        : isSelected || required
                          ? "border-purple-500/50 bg-purple-500/10 ring-2 ring-purple-500/20"
                          : "border-zinc-200 bg-zinc-50 hover:border-zinc-300"
                    } ${required && !isLocked ? "cursor-default opacity-80" : ""}`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className={`text-sm font-medium ${isSelected || required || isLocked ? "text-zinc-950" : "text-zinc-700"}`}>
                        {label}
                      </span>
                      {isLocked && <PmLockBadge pmName={selectedPMInfo?.name} />}
                      {required && !isLocked && (
                        <span className="rounded-full bg-rose-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose-400">
                          필수
                        </span>
                      )}
                      {event && (
                        <span className="rounded-full bg-slate-700/50 px-1.5 py-0.5 text-[10px] text-zinc-500">
                          {event}
                        </span>
                      )}
                    </div>
                    {description && <span className="text-xs text-zinc-500">{description}</span>}
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
