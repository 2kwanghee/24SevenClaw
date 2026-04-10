"use client";

import {
  Bot,
  Server,
  Layout,
  Palette,
  Container,
  Layers,
  Shield,
  Check,
  Users,
  Sparkles,
} from "lucide-react";
import { useEffect, useRef } from "react";

import { useWizardStore } from "@/stores/wizard-store";
import {
  AGENT_RECOMMENDATION_MAP,
  AGENT_REASONING_MAP,
} from "@/hooks/use-recommend";

/* ── 에이전트 카탈로그 ── */

interface AgentCatalogItem {
  id: string;
  name: string;
  description: string;
  outputFiles: string[];
  icon: typeof Bot;
  required: boolean;
}

const AGENT_CATALOG: AgentCatalogItem[] = [
  {
    id: "harness",
    name: "하네스 엔지니어",
    description:
      "Router→Context→Loop→Worker 4단계로 AI 코드 작성을 통제하여 환각과 오류를 사전 차단하는 필수 에이전트",
    outputFiles: ["harness-guide.md"],
    icon: Shield,
    required: true,
  },
  {
    id: "backend",
    name: "시니어 백엔드 엔지니어",
    description:
      "API 엔드포인트 설계, 데이터베이스 모델링, 비즈니스 로직 구현, 인증/인가 처리를 전담하는 백엔드 전문 에이전트",
    outputFiles: ["api-agent.md"],
    icon: Server,
    required: false,
  },
  {
    id: "frontend",
    name: "프론트엔드 전문가",
    description:
      "React/Next.js 컴포넌트 개발, 상태관리 설계, 라우팅 구성, API 연동을 전담하는 프론트엔드 전문 에이전트",
    outputFiles: ["web-agent.md"],
    icon: Layout,
    required: false,
  },
  {
    id: "uiux",
    name: "UI/UX 디자이너",
    description:
      "접근성(WCAG AA) 준수, 반응형 레이아웃, 디자인 시스템 구축, 사용자 경험 최적화를 전담하는 UI/UX 에이전트",
    outputFiles: ["uiux-agent.md"],
    icon: Palette,
    required: false,
  },
  {
    id: "devops",
    name: "DevOps 엔지니어",
    description:
      "Docker 컨테이너화, CI/CD 파이프라인 구축, 배포 자동화, 모니터링/로깅 설정을 전담하는 인프라 에이전트",
    outputFiles: ["infra-agent.md"],
    icon: Container,
    required: false,
  },
  {
    id: "fullstack",
    name: "풀스택 시니어",
    description:
      "프론트엔드와 백엔드를 넘나들며 API 설계부터 UI 구현까지 통합 개발하는 풀스택 에이전트",
    outputFiles: ["fullstack-agent.md"],
    icon: Layers,
    required: false,
  },
];

/* ── 컴포넌트 ── */

export function StepAgents() {
  const agents = useWizardStore((s) => s.data.agents);
  const solutionType = useWizardStore((s) => s.data.solution.solutionType);
  const setAgents = useWizardStore((s) => s.setAgents);
  const hasInitialized = useRef(false);

  // 첫 진입 시 사전 추천 적용 (이미 선택한 항목이 없을 때만)
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    if (agents.selectedAgents.length > 0) return;

    const recommended = solutionType
      ? AGENT_RECOMMENDATION_MAP[solutionType]
      : [];
    // 하네스는 항상 포함
    const initial = Array.from(new Set(["harness", ...recommended]));
    setAgents({ selectedAgents: initial });
  }, [agents.selectedAgents.length, solutionType, setAgents]);

  // 추천 에이전트 ID 목록 + reasoning
  const recommendedIds = solutionType
    ? AGENT_RECOMMENDATION_MAP[solutionType]
    : [];
  const agentReasonings = solutionType
    ? AGENT_REASONING_MAP[solutionType]
    : {};

  const toggleAgent = (id: string) => {
    // 하네스는 해제 불가
    const agent = AGENT_CATALOG.find((a) => a.id === id);
    if (agent?.required) return;

    const current = agents.selectedAgents;
    const next = current.includes(id)
      ? current.filter((a) => a !== id)
      : [...current, id];
    setAgents({ selectedAgents: next });
  };

  const selectedCount = agents.selectedAgents.length;

  return (
    <div className="space-y-6">
      {/* 헤더: 선택된 에이전트 수 */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">
            프로젝트에 투입할 AI 에이전트를 선택하세요
          </p>
          {solutionType && recommendedIds.length > 0 && (
            <p className="mt-1 flex items-center gap-1.5 text-xs text-emerald-400">
              <Sparkles className="h-3 w-3" />
              AI 추천이 반영된 항목 {recommendedIds.length}개
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5">
          <Users className="h-4 w-4 text-violet-400" />
          <span className="text-sm font-medium text-white">
            {selectedCount}
          </span>
          <span className="text-xs text-slate-500">명 선택</span>
        </div>
      </div>

      {/* 에이전트 카드 그리드 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {AGENT_CATALOG.map((agent) => {
          const Icon = agent.icon;
          const selected = agents.selectedAgents.includes(agent.id);
          const isRecommended = recommendedIds.includes(agent.id);
          const reasoning = agentReasonings[agent.id];

          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => toggleAgent(agent.id)}
              disabled={agent.required}
              aria-pressed={selected}
              aria-label={`${agent.name} ${selected ? "선택됨" : "선택 안 됨"}${agent.required ? " (필수)" : ""}${isRecommended ? " (추천)" : ""}`}
              className={`relative flex flex-col gap-3 rounded-xl border px-4 py-4 text-left transition-all duration-200 ${
                agent.required ? "cursor-default" : "hover:scale-[1.02] active:scale-[0.98]"
              } ${
                selected
                  ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/10 ring-2 ring-violet-500/20"
                  : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
              } ${agent.required ? "cursor-default" : "cursor-pointer"} ${isRecommended && !agent.required ? "animate-recommend-glow" : ""}`}
            >
              {/* 선택 표시 배지 */}
              {selected && (
                <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-violet-500">
                  <Check className="h-3 w-3 text-white" />
                </div>
              )}

              {/* 필수 배지 */}
              {agent.required && (
                <span className="absolute left-3 top-3 rounded-md bg-violet-500/20 px-2 py-0.5 text-[10px] font-medium text-violet-300">
                  필수
                </span>
              )}

              {/* 추천 배지 */}
              {isRecommended && !agent.required && (
                <span className="absolute left-3 top-3 flex items-center gap-1 rounded-md bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
                  <Sparkles className="h-2.5 w-2.5" />
                  추천
                </span>
              )}

              {/* 아이콘 + 이름 */}
              <div className={`flex items-center gap-3 ${agent.required || isRecommended ? "mt-4" : ""}`}>
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                    selected
                      ? "bg-violet-500/20"
                      : "bg-white/5"
                  }`}
                >
                  <Icon
                    className={`h-5 w-5 ${selected ? "text-violet-400" : "text-slate-400"}`}
                  />
                </div>
                <span
                  className={`text-sm font-medium ${selected ? "text-white" : "text-slate-300"}`}
                >
                  {agent.name}
                </span>
              </div>

              {/* 역할 설명 */}
              <p className="text-xs leading-relaxed text-slate-500">
                {agent.description}
              </p>

              {/* 추천 사유 */}
              {isRecommended && reasoning && (
                <p className="flex items-start gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-2 text-[11px] leading-relaxed text-emerald-300">
                  <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
                  {reasoning}
                </p>
              )}

              {/* 생성 파일 목록 */}
              <div className="flex flex-wrap gap-1.5">
                {agent.outputFiles.map((file) => (
                  <span
                    key={file}
                    className={`rounded-md px-2 py-0.5 text-[11px] ${
                      selected
                        ? "bg-violet-500/20 text-violet-300"
                        : "bg-white/5 text-slate-500"
                    }`}
                  >
                    {file}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
