"use client";

import {
  Wrench,
  TestTube,
  Layers,
  SearchCheck,
  Github,
  BarChart3,
  FileText,
  MessageSquare,
  Send,
  Database,
  Users,
  Check,
  Key,
  Eye,
  EyeOff,
  Info,
  Workflow,
  Plug,
  Sparkles,
} from "lucide-react";
import { useState, useCallback, useEffect, useRef } from "react";

import { useWizardStore } from "@/stores/wizard-store";
import type { SkillSelection } from "@/types/wizard";

/* ── 스킬 카탈로그 ── */

interface SkillCatalogItem {
  id: string;
  name: string;
  description: string;
  /** 이 스킬을 사용하면 좋은 상황 (1줄) */
  whenToUse?: string;
  type: "workflow" | "external-tool";
  category: string;
  compatibleAgents: string[];
  tags: string[];
  icon: typeof Wrench;
  apiKeyField?: string;
  envVar?: string;
}

const SKILL_CATALOG: SkillCatalogItem[] = [
  // --- Workflow Skills ---
  {
    id: "tdd-smart-coding",
    name: "TDD Smart Coding",
    description:
      "Red-Green-Refactor 사이클로 테스트 먼저 작성 → 코드 구현 → 리팩토링을 자동 반복. 커버리지 미달 시 재시도",
    whenToUse:
      "새 기능 구현 시 테스트 커버리지를 확실히 확보하고 싶을 때",
    type: "workflow",
    category: "development",
    compatibleAgents: ["claude-code", "gemini-cli"],
    tags: ["tdd", "testing", "workflow"],
    icon: TestTube,
  },
  {
    id: "fullstack",
    name: "Fullstack Development",
    description:
      "FastAPI 백엔드 + Next.js 프론트엔드를 동시에 다루는 풀스택 개발 워크플로. API ↔ UI 연동까지 일관 처리",
    whenToUse:
      "백엔드 API와 프론트엔드 UI를 함께 개발할 때",
    type: "workflow",
    category: "development",
    compatibleAgents: ["claude-code", "cursor"],
    tags: ["fullstack", "backend", "frontend"],
    icon: Layers,
  },
  {
    id: "code-review",
    name: "Code Review",
    description:
      "코드 변경마다 보안·성능·가독성을 AI가 자동 리뷰하고 구체적 개선안을 제시. PR 품질을 사전에 높임",
    whenToUse:
      "코드 품질을 자동으로 검증하고 사람 리뷰 전에 문제를 잡고 싶을 때",
    type: "workflow",
    category: "quality",
    compatibleAgents: ["claude-code", "gemini-cli", "codex"],
    tags: ["review", "quality", "automation"],
    icon: SearchCheck,
  },
  // --- External Tool Skills ---
  {
    id: "github",
    name: "GitHub",
    description:
      "GitHub 리포지토리, 이슈, PR을 AI 에이전트가 직접 조회·생성·관리. 코드 리뷰와 이슈 추적을 자동화",
    whenToUse:
      "AI가 GitHub 이슈/PR을 직접 다루게 하고 싶을 때",
    type: "external-tool",
    category: "integration",
    compatibleAgents: ["claude-code", "gemini-cli", "codex", "cursor"],
    tags: ["github", "vcs", "mcp"],
    icon: Github,
    apiKeyField: "github_token",
    envVar: "GITHUB_TOKEN",
  },
  {
    id: "linear-mcp",
    name: "Linear MCP",
    description:
      "Linear 이슈를 코드 작업과 연동하여 상태를 자동 동기화. 커밋 시 이슈 상태를 In Progress → Done으로 전환",
    whenToUse:
      "Linear로 프로젝트를 관리하며 이슈 상태를 코드와 자동 연동하고 싶을 때",
    type: "external-tool",
    category: "integration",
    compatibleAgents: ["claude-code"],
    tags: ["linear", "project-management", "mcp"],
    icon: BarChart3,
  },
  {
    id: "notion",
    name: "Notion",
    description:
      "Notion 워크스페이스의 페이지와 데이터베이스를 AI가 직접 읽고 쓰기. 문서화와 지식 관리를 자동화",
    whenToUse:
      "Notion에 저장된 기획서나 문서를 AI가 참조하거나 업데이트하게 하고 싶을 때",
    type: "external-tool",
    category: "integration",
    compatibleAgents: ["claude-code", "cursor"],
    tags: ["notion", "documentation", "mcp"],
    icon: FileText,
    apiKeyField: "notion_api_key",
    envVar: "NOTION_API_KEY",
  },
  {
    id: "slack",
    name: "Slack",
    description:
      "Slack 채널로 파이프라인 결과, 에러 알림, PR 생성 등 주요 이벤트를 자동 전송. 팀 협업에 실시간 연동",
    whenToUse:
      "개발 이벤트를 Slack 채널로 실시간 알림받고 싶을 때",
    type: "external-tool",
    category: "integration",
    compatibleAgents: ["claude-code", "gemini-cli", "cursor"],
    tags: ["slack", "messaging", "notification"],
    icon: MessageSquare,
    apiKeyField: "slack_bot_token",
    envVar: "SLACK_BOT_TOKEN",
  },
  {
    id: "telegram",
    name: "Telegram",
    description:
      "Telegram 봇을 통해 파이프라인 완료·실패·PR 생성 등 개발 이벤트를 모바일로 즉시 알림. 양방향 상호작용 지원",
    whenToUse:
      "모바일로 개발 상황을 실시간 추적하고 원격 제어하고 싶을 때",
    type: "external-tool",
    category: "integration",
    compatibleAgents: ["claude-code", "gemini-cli"],
    tags: ["telegram", "bot", "notification"],
    icon: Send,
    apiKeyField: "telegram_bot_token",
    envVar: "TELEGRAM_BOT_TOKEN",
  },
  {
    id: "teams",
    name: "Microsoft Teams",
    description:
      "Microsoft Teams 채널로 개발 이벤트 알림을 자동 전송. Webhook 기반으로 설정이 간편하고 기업 환경에 최적화",
    whenToUse:
      "기업 환경에서 Teams로 개발 알림을 받고 싶을 때",
    type: "external-tool",
    category: "integration",
    compatibleAgents: ["claude-code", "cursor"],
    tags: ["teams", "microsoft", "messaging"],
    icon: Users,
    apiKeyField: "teams_webhook_url",
    envVar: "TEAMS_WEBHOOK_URL",
  },
  {
    id: "database",
    name: "Database",
    description:
      "PostgreSQL, MySQL, SQLite 등 데이터베이스에 AI가 직접 연결하여 스키마 조회, 쿼리 실행, 데이터 분석 수행",
    whenToUse:
      "AI가 DB 스키마를 참조하거나 쿼리를 직접 실행하게 하고 싶을 때",
    type: "external-tool",
    category: "integration",
    compatibleAgents: ["claude-code", "gemini-cli", "cursor"],
    tags: ["database", "sql", "mcp"],
    icon: Database,
    apiKeyField: "database_url",
    envVar: "DATABASE_URL",
  },
];

const WORKFLOW_SKILLS = SKILL_CATALOG.filter((s) => s.type === "workflow");
const EXTERNAL_SKILLS = SKILL_CATALOG.filter((s) => s.type === "external-tool");

/* ── 컴포넌트 ── */

export function StepSkills() {
  const skills = useWizardStore((s) => s.data.skills);
  const setSkills = useWizardStore((s) => s.setSkills);
  const recommendations = useWizardStore((s) => s.recommendations);
  const hasInitialized = useRef(false);

  // API 키 마스킹 토글 상태 (스킬 ID → 표시 여부)
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});

  // 추천 스킬 ID 목록 + reasoning
  const recommendedSkillIds = recommendations?.skills ?? [];
  const skillReasonings = recommendations?.skillReasonings ?? {};

  // 첫 진입 시 추천 스킬 사전 선택 (이미 선택한 항목이 없을 때만)
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    if (skills.selectedSkills.length > 0) return;
    if (recommendedSkillIds.length === 0) return;

    const initial: SkillSelection[] = recommendedSkillIds
      .filter((id) => SKILL_CATALOG.some((s) => s.id === id))
      .map((id) => ({ id }));
    if (initial.length > 0) {
      setSkills({ selectedSkills: initial });
    }
  }, [skills.selectedSkills.length, recommendedSkillIds, setSkills]);

  const isSelected = useCallback(
    (id: string) => skills.selectedSkills.some((s) => s.id === id),
    [skills.selectedSkills],
  );

  const getApiKey = useCallback(
    (id: string) =>
      skills.selectedSkills.find((s) => s.id === id)?.apiKey ?? "",
    [skills.selectedSkills],
  );

  const toggleSkill = (id: string) => {
    const current = skills.selectedSkills;
    if (isSelected(id)) {
      setSkills({
        selectedSkills: current.filter((s) => s.id !== id),
      });
    } else {
      const newSelection: SkillSelection = { id };
      setSkills({
        selectedSkills: [...current, newSelection],
      });
    }
  };

  const updateApiKey = (id: string, apiKey: string) => {
    setSkills({
      selectedSkills: skills.selectedSkills.map((s) =>
        s.id === id ? { ...s, apiKey } : s,
      ),
    });
  };

  const toggleKeyVisibility = (id: string) => {
    setVisibleKeys((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const selectedCount = skills.selectedSkills.length;

  return (
    <div className="space-y-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-300">
            프로젝트에 장착할 스킬과 외부 도구를 선택하세요
          </p>
          {recommendedSkillIds.length > 0 && (
            <p className="mt-1 flex items-center gap-1.5 text-xs text-emerald-400">
              <Sparkles className="h-3 w-3" />
              AI 추천이 반영된 항목 {recommendedSkillIds.length}개
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5">
          <Wrench className="h-4 w-4 text-violet-400" />
          <span className="text-sm font-medium text-white">
            {selectedCount}
          </span>
          <span className="text-xs text-slate-500">개 선택</span>
        </div>
      </div>

      {/* 워크플로우 스킬 섹션 */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Workflow className="h-4 w-4 text-violet-400" />
          <h3 className="text-sm font-medium text-slate-200">
            워크플로우 스킬
          </h3>
          <span className="text-xs text-slate-500">
            개발 프로세스 자동화
          </span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {WORKFLOW_SKILLS.map((skill) => (
            <SkillCard
              key={skill.id}
              skill={skill}
              selected={isSelected(skill.id)}
              recommended={recommendedSkillIds.includes(skill.id)}
              reasoning={skillReasonings[skill.id]}
              onToggle={toggleSkill}
            />
          ))}
        </div>
      </section>

      {/* 외부 도구 스킬 섹션 */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Plug className="h-4 w-4 text-violet-400" />
          <h3 className="text-sm font-medium text-slate-200">
            외부 도구 연동
          </h3>
          <span className="text-xs text-slate-500">
            API 키가 필요할 수 있습니다
          </span>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {EXTERNAL_SKILLS.map((skill) => (
            <SkillCard
              key={skill.id}
              skill={skill}
              selected={isSelected(skill.id)}
              recommended={recommendedSkillIds.includes(skill.id)}
              reasoning={skillReasonings[skill.id]}
              apiKey={getApiKey(skill.id)}
              keyVisible={visibleKeys[skill.id] ?? false}
              onToggle={toggleSkill}
              onApiKeyChange={updateApiKey}
              onToggleKeyVisibility={toggleKeyVisibility}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

/* ── 스킬 카드 ── */

interface SkillCardProps {
  skill: SkillCatalogItem;
  selected: boolean;
  recommended: boolean;
  reasoning?: string;
  apiKey?: string;
  keyVisible?: boolean;
  onToggle: (id: string) => void;
  onApiKeyChange?: (id: string, key: string) => void;
  onToggleKeyVisibility?: (id: string) => void;
}

function SkillCard({
  skill,
  selected,
  recommended,
  reasoning,
  apiKey,
  keyVisible,
  onToggle,
  onApiKeyChange,
  onToggleKeyVisibility,
}: SkillCardProps) {
  const Icon = skill.icon;
  const needsApiKey = selected && skill.apiKeyField;

  return (
    <div
      className={`relative flex flex-col gap-3 rounded-xl border px-4 py-4 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${
        selected
          ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/10 ring-2 ring-violet-500/20"
          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
      } ${recommended ? "animate-recommend-glow" : ""}`}
    >
      {/* 추천 배지 */}
      {recommended && (
        <span className="absolute left-3 top-3 flex items-center gap-1 rounded-md bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
          <Sparkles className="h-2.5 w-2.5" />
          추천
        </span>
      )}

      {/* 선택 토글 영역 */}
      <button
        type="button"
        onClick={() => onToggle(skill.id)}
        aria-pressed={selected}
        aria-label={`${skill.name} ${selected ? "선택됨" : "선택 안 됨"}${recommended ? " (추천)" : ""}`}
        className={`flex w-full items-start gap-3 text-left ${recommended ? "mt-4" : ""}`}
      >
        {/* 선택 표시 배지 */}
        {selected && (
          <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-violet-500">
            <Check className="h-3 w-3 text-white" />
          </div>
        )}

        {/* 아이콘 + 이름 */}
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
            selected ? "bg-violet-500/20" : "bg-white/5"
          }`}
        >
          <Icon
            className={`h-5 w-5 ${selected ? "text-violet-400" : "text-slate-400"}`}
          />
        </div>
        <div className="min-w-0 flex-1">
          <span
            className={`text-sm font-medium ${selected ? "text-white" : "text-slate-300"}`}
          >
            {skill.name}
          </span>
          <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
            {skill.description}
          </p>
          {skill.whenToUse && (
            <p className="mt-1 flex items-center gap-1 text-[11px] text-slate-400">
              <Info className="h-3 w-3 shrink-0 text-slate-500" />
              {skill.whenToUse}
            </p>
          )}
        </div>
      </button>

      {/* 태그 */}
      <div className="flex flex-wrap gap-1.5">
        {skill.tags.map((tag) => (
          <span
            key={tag}
            className={`rounded-md px-2 py-0.5 text-[11px] ${
              selected
                ? "bg-violet-500/20 text-violet-300"
                : "bg-white/5 text-slate-500"
            }`}
          >
            {tag}
          </span>
        ))}
      </div>

      {/* 추천 사유 */}
      {recommended && reasoning && (
        <p className="flex items-start gap-1.5 rounded-lg bg-emerald-500/10 px-2.5 py-2 text-[11px] leading-relaxed text-emerald-300">
          <Sparkles className="mt-0.5 h-3 w-3 shrink-0" />
          {reasoning}
        </p>
      )}

      {/* API 키 입력 (선택된 외부 도구만) */}
      {needsApiKey && (
        <div className="space-y-1.5 border-t border-white/5 pt-3">
          <div className="flex items-center gap-1.5">
            <Key className="h-3 w-3 text-slate-500" />
            <span className="text-[11px] font-medium text-slate-400">
              API Key
            </span>
          </div>
          <div className="relative">
            <input
              type={keyVisible ? "text" : "password"}
              value={apiKey ?? ""}
              onChange={(e) => onApiKeyChange?.(skill.id, e.target.value)}
              placeholder={`${skill.envVar} 값 입력`}
              aria-label={`${skill.name} API 키 입력`}
              className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-3 pr-9 text-xs text-white placeholder-slate-600 focus:border-violet-500/50 focus:bg-white/[0.07] focus:outline-none focus:ring-2 focus:ring-violet-500/20"
            />
            <button
              type="button"
              onClick={() => onToggleKeyVisibility?.(skill.id)}
              aria-label={keyVisible ? "키 숨기기" : "키 보기"}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              {keyVisible ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
          <p className="flex items-center gap-1 text-[10px] text-slate-600">
            <Info className="h-2.5 w-2.5" />
            <span>
              .env 파일에{" "}
              <code className="rounded bg-white/5 px-1 py-0.5 font-mono text-slate-400">
                {skill.envVar}
              </code>
              로 저장됩니다
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
