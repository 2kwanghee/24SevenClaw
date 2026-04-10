"use client";

import {
  Monitor,
  Terminal,
  MousePointerClick,
  Bot,
  Check,
  FolderTree,
  ChevronRight,
} from "lucide-react";

import { PLATFORM_DIR_MAP } from "@/lib/engine/platforms/types";
import type { PlatformId } from "@/lib/engine/platforms/types";
import { useWizardStore } from "@/stores/wizard-store";

/* ── 플랫폼 카탈로그 ── */

interface PlatformCatalogItem {
  id: PlatformId;
  name: string;
  description: string;
  icon: typeof Monitor;
  /** 생성되는 폴더 구조 프리뷰 */
  folderPreview: string[];
}

const PLATFORM_CATALOG: PlatformCatalogItem[] = [
  {
    id: "claude-code",
    name: "Claude Code",
    description: "Anthropic의 터미널 기반 AI 코딩 에이전트. CLAUDE.md로 프로젝트 컨텍스트를 관리",
    icon: Terminal,
    folderPreview: [
      PLATFORM_DIR_MAP["claude-code"].configDir + "/",
      PLATFORM_DIR_MAP["claude-code"].agentDir + "/",
      PLATFORM_DIR_MAP["claude-code"].settingsFile,
      PLATFORM_DIR_MAP["claude-code"].rootGuide,
    ],
  },
  {
    id: "gemini-cli",
    name: "Gemini CLI",
    description: "Google의 터미널 AI 코딩 에이전트. GEMINI.md로 프로젝트 지침을 전달",
    icon: Bot,
    folderPreview: [
      PLATFORM_DIR_MAP["gemini-cli"].configDir + "/",
      PLATFORM_DIR_MAP["gemini-cli"].agentDir + "/",
      PLATFORM_DIR_MAP["gemini-cli"].settingsFile,
      PLATFORM_DIR_MAP["gemini-cli"].rootGuide,
    ],
  },
  {
    id: "codex",
    name: "Codex",
    description: "OpenAI의 터미널 AI 코딩 에이전트. CODEX.md로 프로젝트 가이드를 정의",
    icon: Terminal,
    folderPreview: [
      PLATFORM_DIR_MAP["codex"].configDir + "/",
      PLATFORM_DIR_MAP["codex"].agentDir + "/",
      PLATFORM_DIR_MAP["codex"].settingsFile,
      PLATFORM_DIR_MAP["codex"].rootGuide,
    ],
  },
  {
    id: "cursor",
    name: "Cursor",
    description: "AI 네이티브 IDE. .cursorrules로 프로젝트 규칙을 설정하고 에디터 내에서 AI 지원",
    icon: MousePointerClick,
    folderPreview: [
      PLATFORM_DIR_MAP["cursor"].configDir + "/",
      PLATFORM_DIR_MAP["cursor"].agentDir + "/",
      PLATFORM_DIR_MAP["cursor"].settingsFile,
      PLATFORM_DIR_MAP["cursor"].rootGuide,
    ],
  },
];

/* ── 컴포넌트 ── */

export function StepPlatform() {
  const platform = useWizardStore((s) => s.data.platform);
  const setPlatform = useWizardStore((s) => s.setPlatform);

  const selectPlatform = (id: PlatformId) => {
    setPlatform({ platformId: platform.platformId === id ? null : id });
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-300">
          프로젝트에서 사용할 AI 코딩 플랫폼을 선택하세요
        </p>
        {platform.platformId && (
          <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5">
            <Monitor className="h-4 w-4 text-violet-400" />
            <span className="text-sm font-medium text-white">1</span>
            <span className="text-xs text-slate-500">개 선택</span>
          </div>
        )}
      </div>

      {/* 플랫폼 카드 그리드 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {PLATFORM_CATALOG.map((item) => (
          <PlatformCard
            key={item.id}
            item={item}
            selected={platform.platformId === item.id}
            onSelect={selectPlatform}
          />
        ))}
      </div>

      {/* 선택된 플랫폼의 폴더 구조 프리뷰 */}
      {platform.platformId && (
        <FolderPreview
          item={PLATFORM_CATALOG.find((p) => p.id === platform.platformId)!}
        />
      )}
    </div>
  );
}

/* ── 플랫폼 카드 ── */

interface PlatformCardProps {
  item: PlatformCatalogItem;
  selected: boolean;
  onSelect: (id: PlatformId) => void;
}

function PlatformCard({ item, selected, onSelect }: PlatformCardProps) {
  const Icon = item.icon;

  return (
    <button
      type="button"
      onClick={() => onSelect(item.id)}
      aria-pressed={selected}
      aria-label={`${item.name} ${selected ? "선택됨" : "선택"}`}
      className={`relative flex flex-col gap-3 rounded-xl border px-4 py-4 text-left transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${
        selected
          ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/10 ring-2 ring-violet-500/20"
          : "cursor-pointer border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
      }`}
    >
      {/* 선택 표시 배지 */}
      {selected && (
        <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-violet-500">
          <Check className="h-3 w-3 text-white" />
        </div>
      )}

      {/* 아이콘 + 이름 */}
      <div className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
            selected ? "bg-violet-500/20" : "bg-white/5"
          }`}
        >
          <Icon
            className={`h-5 w-5 ${
              selected ? "text-violet-400" : "text-slate-400"
            }`}
          />
        </div>
        <span
          className={`text-sm font-medium ${
            selected ? "text-white" : "text-slate-300"
          }`}
        >
          {item.name}
        </span>
      </div>

      {/* 설명 */}
      <p className="text-xs leading-relaxed text-slate-500">
        {item.description}
      </p>
    </button>
  );
}

/* ── 폴더 구조 프리뷰 ── */

interface FolderPreviewProps {
  item: PlatformCatalogItem;
}

function FolderPreview({ item }: FolderPreviewProps) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-3 flex items-center gap-2">
        <FolderTree className="h-4 w-4 text-violet-400" />
        <span className="text-xs font-medium text-slate-300">
          {item.name} 생성 폴더 구조
        </span>
      </div>
      <div className="space-y-1">
        {item.folderPreview.map((path) => (
          <div key={path} className="flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3 text-slate-600" />
            <code className="text-xs text-slate-400">{path}</code>
          </div>
        ))}
      </div>
    </div>
  );
}
