"use client";

import {
  GitBranch,
  Shield,
  TestTube,
  SearchCheck,
  Send,
  ShieldCheck,
  RefreshCw,
  Check,
  AlertTriangle,
  Info,
  Link2,
  Sparkles,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef } from "react";

import { useWizardStore } from "@/stores/wizard-store";

/* ── 파이프라인 카탈로그 ── */

interface PipelineCatalogItem {
  id: string;
  name: string;
  description: string;
  icon: typeof GitBranch;
  /** Step 4에서 선택해야 하는 스킬 ID (의존성) */
  requiredSkillIds: string[];
  /** 의존성 안내 메시지 */
  dependencyHint?: string;
  /** 연관 스킬 ID (선택적 연동 표시) */
  relatedSkillIds: string[];
}

const PIPELINE_CATALOG: PipelineCatalogItem[] = [
  {
    id: "harness",
    name: "하네스 엔지니어링",
    description:
      "Router → Context → Loop → Worker 4단계 품질 통제 파이프라인",
    icon: Shield,
    requiredSkillIds: [],
    relatedSkillIds: [],
  },
  {
    id: "tdd",
    name: "TDD Smart Coding",
    description:
      "테스트 작성 → 구현 → 리팩토링 자동 순환. 커버리지 미달 시 반복",
    icon: TestTube,
    requiredSkillIds: [],
    relatedSkillIds: ["tdd-smart-coding"],
  },
  {
    id: "ai-review",
    name: "AI 코드 리뷰",
    description:
      "코드 변경마다 AI가 보안·성능·품질 리뷰 후 승인/반려 판단",
    icon: SearchCheck,
    requiredSkillIds: [],
    relatedSkillIds: ["code-review"],
  },
  {
    id: "telegram-notify",
    name: "텔레그램 알림",
    description:
      "파이프라인 완료·실패·PR 생성 등 주요 이벤트를 텔레그램으로 알림",
    icon: Send,
    requiredSkillIds: ["telegram"],
    dependencyHint: "Step 4에서 Telegram API 키를 설정해야 합니다",
    relatedSkillIds: ["telegram"],
  },
  {
    id: "lint-gate",
    name: "린트 Gate",
    description:
      "커밋 전 ESLint/Ruff/Prettier 자동 실행. 통과해야 커밋 허용",
    icon: ShieldCheck,
    requiredSkillIds: [],
    relatedSkillIds: [],
  },
  {
    id: "ralph-loop",
    name: "Ralph 루프",
    description:
      "fix_plan.md 기반 자율 개발 루프. 항목별 구현 → 테스트 → 커밋 반복",
    icon: RefreshCw,
    requiredSkillIds: [],
    relatedSkillIds: [],
  },
];

/* ── 파이프라인 조합 시너지 맵 ── */

interface SynergyEntry {
  /** 조합에 필요한 파이프라인 ID 집합 */
  pipelineIds: string[];
  /** 시너지 조합 이름 */
  name: string;
  /** 시너지 효과 설명 */
  description: string;
}

const SYNERGY_MAP: SynergyEntry[] = [
  {
    pipelineIds: ["harness", "tdd", "ai-review"],
    name: "완전 자동화 품질 루프",
    description:
      "코드 작성 → 자동 테스트 → AI 리뷰 → 개선이 완전 자동화되는 최강 품질 파이프라인",
  },
  {
    pipelineIds: ["ralph-loop", "harness"],
    name: "안전한 자율 개발",
    description:
      "Ralph가 자율 개발하되, 하네스가 매 단계 품질을 통제하여 안전한 무인 개발을 실현합니다",
  },
  {
    pipelineIds: ["harness", "tdd"],
    name: "하네스 + TDD 품질 보장",
    description:
      "하네스 품질 통제 아래 TDD 루프가 돌면서 코드 작성 → 테스트 → 검증이 자동 반복됩니다",
  },
  {
    pipelineIds: ["harness", "ai-review"],
    name: "이중 품질 검증",
    description:
      "하네스가 코드 품질을 통제하고, AI 리뷰가 보안·성능·가독성을 이중 검증합니다",
  },
  {
    pipelineIds: ["tdd", "ai-review"],
    name: "테스트 + 리뷰 안전망",
    description:
      "TDD로 테스트 커버리지를 확보하고, AI 리뷰가 코드 품질을 추가 검증하는 이중 안전망",
  },
  {
    pipelineIds: ["lint-gate", "ai-review"],
    name: "코드 표준 강제",
    description:
      "린트로 코딩 스타일을 일관되게 유지하고, AI 리뷰로 로직 품질까지 검증합니다",
  },
];

/** 선택된 파이프라인으로 활성화되는 시너지를 찾는다 (큰 조합 우선) */
function findActiveSynergies(selectedIds: string[]): SynergyEntry[] {
  return SYNERGY_MAP.filter((entry) =>
    entry.pipelineIds.every((id) => selectedIds.includes(id)),
  );
}

/* ── 컴포넌트 ── */

export function StepPipelines() {
  const pipelines = useWizardStore((s) => s.data.pipelines);
  const selectedSkills = useWizardStore((s) => s.data.skills.selectedSkills);
  const setPipelines = useWizardStore((s) => s.setPipelines);
  const recommendations = useWizardStore((s) => s.recommendations);
  const hasInitialized = useRef(false);

  const selectedSkillIds = selectedSkills.map((s) => s.id);

  // 추천 파이프라인 ID 목록 + reasoning
  const recommendedPipelineIds = recommendations?.pipelines ?? [];
  const pipelineReasonings = recommendations?.pipelineReasonings ?? {};

  // 첫 진입 시 추천 파이프라인 사전 선택 (이미 선택한 항목이 없을 때만)
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    if (pipelines.selectedPipelines.length > 0) return;
    if (recommendedPipelineIds.length === 0) return;

    // 의존성이 충족된 추천 파이프라인만 선택
    const initial = recommendedPipelineIds.filter((id) => {
      const item = PIPELINE_CATALOG.find((p) => p.id === id);
      if (!item) return false;
      return (
        item.requiredSkillIds.length === 0 ||
        item.requiredSkillIds.every((sid) => selectedSkillIds.includes(sid))
      );
    });
    if (initial.length > 0) {
      setPipelines({ selectedPipelines: initial });
    }
  }, [pipelines.selectedPipelines.length, recommendedPipelineIds, selectedSkillIds, setPipelines]);

  const isSelected = useCallback(
    (id: string) => pipelines.selectedPipelines.includes(id),
    [pipelines.selectedPipelines],
  );

  const togglePipeline = (id: string) => {
    const current = pipelines.selectedPipelines;
    const next = current.includes(id)
      ? current.filter((p) => p !== id)
      : [...current, id];
    setPipelines({ selectedPipelines: next });
  };

  /** 의존 스킬이 Step 4에서 선택되었는지 확인 */
  const hasDependency = useCallback(
    (item: PipelineCatalogItem) =>
      item.requiredSkillIds.length === 0 ||
      item.requiredSkillIds.every((sid) => selectedSkillIds.includes(sid)),
    [selectedSkillIds],
  );

  /** Step 4에서 선택한 스킬 중 연관된 것이 있는지 */
  const hasRelatedSkill = useCallback(
    (item: PipelineCatalogItem) =>
      item.relatedSkillIds.some((sid) => selectedSkillIds.includes(sid)),
    [selectedSkillIds],
  );

  const selectedCount = pipelines.selectedPipelines.length;

  const activeSynergies = useMemo(
    () => findActiveSynergies(pipelines.selectedPipelines),
    [pipelines.selectedPipelines],
  );

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">
            프로젝트에 적용할 자동화 파이프라인을 선택하세요
          </p>
          {recommendedPipelineIds.length > 0 && (
            <p className="mt-1 flex items-center gap-1.5 text-xs text-emerald-400">
              <Sparkles className="h-3 w-3" />
              AI 추천이 반영된 항목 {recommendedPipelineIds.length}개
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5">
          <GitBranch className="h-4 w-4 text-violet-400" />
          <span className="text-sm font-medium text-white">
            {selectedCount}
          </span>
          <span className="text-xs text-slate-500">개 선택</span>
        </div>
      </div>

      {/* 파이프라인 카드 그리드 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {PIPELINE_CATALOG.map((item) => {
          const depMet = hasDependency(item);
          const related = hasRelatedSkill(item);

          return (
            <PipelineCard
              key={item.id}
              item={item}
              selected={isSelected(item.id)}
              recommended={recommendedPipelineIds.includes(item.id)}
              reasoning={pipelineReasonings[item.id]}
              dependencyMet={depMet}
              hasRelatedSkill={related}
              onToggle={togglePipeline}
            />
          );
        })}
      </div>

      {/* 시너지 효과 카드 */}
      {activeSynergies.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-amber-400" />
            <h3 className="text-sm font-medium text-slate-200">
              조합 시너지 효과
            </h3>
            <span className="text-xs text-slate-500">
              선택한 파이프라인의 시너지
            </span>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {activeSynergies.map((synergy) => (
              <div
                key={synergy.pipelineIds.join("-")}
                className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3"
              >
                <Zap className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-amber-200">
                    {synergy.name}
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-amber-300/70">
                    {synergy.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── 파이프라인 카드 ── */

interface PipelineCardProps {
  item: PipelineCatalogItem;
  selected: boolean;
  recommended: boolean;
  reasoning?: string;
  dependencyMet: boolean;
  hasRelatedSkill: boolean;
  onToggle: (id: string) => void;
}

function PipelineCard({
  item,
  selected,
  recommended,
  reasoning,
  dependencyMet,
  hasRelatedSkill,
  onToggle,
}: PipelineCardProps) {
  const Icon = item.icon;
  const disabled = !dependencyMet;

  return (
    <button
      type="button"
      onClick={() => !disabled && onToggle(item.id)}
      disabled={disabled}
      aria-pressed={selected}
      aria-label={`${item.name} ${selected ? "활성" : "비활성"}${disabled ? " (의존성 미충족)" : ""}${recommended ? " (추천)" : ""}`}
      className={`relative flex flex-col gap-3 rounded-xl border px-4 py-4 text-left transition-all duration-200 ${
        disabled
          ? "cursor-not-allowed border-white/5 bg-white/[0.02] opacity-50"
          : selected
            ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/10 ring-2 ring-violet-500/20"
            : "cursor-pointer border-white/10 bg-white/5 hover:scale-[1.02] hover:border-white/20 hover:bg-white/[0.07] active:scale-[0.98]"
      } ${recommended && !disabled ? "animate-recommend-glow" : ""}`}
    >
      {/* 추천 배지 */}
      {recommended && !disabled && (
        <span className="absolute left-3 top-3 flex items-center gap-1 rounded-md bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
          <Sparkles className="h-2.5 w-2.5" />
          추천
        </span>
      )}

      {/* 선택 표시 배지 */}
      {selected && !disabled && (
        <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-violet-500">
          <Check className="h-3 w-3 text-white" />
        </div>
      )}

      {/* 아이콘 + 이름 */}
      <div className={`flex items-center gap-3 ${recommended && !disabled ? "mt-4" : ""}`}>
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
            selected && !disabled ? "bg-violet-500/20" : "bg-white/5"
          }`}
        >
          <Icon
            className={`h-5 w-5 ${
              selected && !disabled ? "text-violet-400" : "text-slate-400"
            }`}
          />
        </div>
        <span
          className={`text-sm font-medium ${
            selected && !disabled ? "text-white" : "text-slate-300"
          }`}
        >
          {item.name}
        </span>
      </div>

      {/* 설명 */}
      <p className="text-xs leading-relaxed text-slate-500">
        {item.description}
      </p>

      {/* 추천 사유 */}
      {recommended && !disabled && reasoning && (
        <p className="flex items-start gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-2 text-[11px] leading-relaxed text-emerald-300">
          <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
          {reasoning}
        </p>
      )}

      {/* 의존성 경고 (미충족 시) */}
      {disabled && item.dependencyHint && (
        <div className="flex items-start gap-1.5 rounded-lg bg-amber-500/10 px-2.5 py-2">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />
          <span className="text-[11px] leading-relaxed text-amber-300">
            {item.dependencyHint}
          </span>
        </div>
      )}

      {/* Step 4 연동 표시 (관련 스킬이 선택되었을 때) */}
      {!disabled && hasRelatedSkill && (
        <div className="flex items-center gap-1.5">
          <Link2 className="h-3 w-3 text-emerald-400" />
          <span className="text-[11px] text-emerald-400">
            Step 4 스킬과 연동됨
          </span>
        </div>
      )}

      {/* 의존 스킬 안내 (충족되었지만 존재할 때) */}
      {!disabled && item.requiredSkillIds.length > 0 && (
        <div className="flex items-center gap-1.5">
          <Info className="h-3 w-3 text-slate-500" />
          <span className="text-[11px] text-slate-500">
            필요 스킬 설정 완료
          </span>
        </div>
      )}
    </button>
  );
}
