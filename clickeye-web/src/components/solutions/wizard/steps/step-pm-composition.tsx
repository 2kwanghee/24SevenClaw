"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  ChevronDown,
  ChevronRight,
  Info,
  Loader2,
  Puzzle,
  RefreshCw,
  Server,
  UserCircle2,
  Webhook,
  Wrench,
} from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { pmProfiles, type PMCompositionResponse } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/* -- 상수 -------------------------------------------------------------- */

/** SOLUTION_WIZARD_STEPS 기준 PM 선택 스텝 인덱스 */
const PM_SELECTION_STEP = 4;

const CATEGORY_CONFIG = [
  {
    key: "agents" as const,
    label: "AI 에이전트",
    icon: Bot,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    border: "border-zinc-200",
  },
  {
    key: "skills" as const,
    label: "스킬",
    icon: Wrench,
    color: "text-sky-400",
    bg: "bg-sky-500/10",
    border: "border-sky-500/20",
  },
  {
    key: "hooks" as const,
    label: "훅",
    icon: Webhook,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
    border: "border-violet-500/20",
  },
  {
    key: "mcp_servers" as const,
    label: "MCP 서버",
    icon: Server,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
  },
  {
    key: "plugins" as const,
    label: "플러그인",
    icon: Puzzle,
    color: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/20",
  },
] as const;

type CategoryKey = (typeof CATEGORY_CONFIG)[number]["key"];

/* -- 카테고리 섹션 컴포넌트 --------------------------------------------- */

interface CompositionSectionProps {
  label: string;
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  color: string;
  bg: string;
  border: string;
  items: PMCompositionResponse[];
}

function CompositionSection({
  label,
  icon: Icon,
  color,
  bg,
  border,
  items,
}: CompositionSectionProps) {
  const [isOpen, setIsOpen] = useState(true);

  if (items.length === 0) return null;

  return (
    <div className={cn("overflow-hidden rounded-xl border", border)}>
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 transition-colors hover:bg-zinc-50"
        aria-expanded={isOpen}
        aria-controls={`section-${label}`}
      >
        <div className="flex items-center gap-2.5">
          <div
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-lg",
              bg,
            )}
          >
            <Icon className={cn("h-4 w-4", color)} aria-hidden={true} />
          </div>
          <span className="text-sm font-medium text-zinc-950">{label}</span>
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">
            {items.length}
          </span>
        </div>
        {isOpen ? (
          <ChevronDown
            className="h-4 w-4 text-zinc-500"
            aria-hidden={true}
          />
        ) : (
          <ChevronRight
            className="h-4 w-4 text-zinc-500"
            aria-hidden={true}
          />
        )}
      </button>

      {isOpen && (
        <div
          id={`section-${label}`}
          className="border-t border-zinc-100 px-4 py-2"
        >
          <ul className="space-y-1" role="list">
            {items.map((item) => {
              const desc =
                typeof item.config.description === "string"
                  ? item.config.description
                  : null;

              return (
                <li
                  key={item.id}
                  className="flex items-start gap-2 rounded-lg py-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-medium text-zinc-700">
                        {item.component_name}
                      </span>
                      <code className="rounded bg-zinc-50 px-1 py-0.5 font-mono text-xs text-zinc-500">
                        {item.component_slug}
                      </code>
                      <span
                        className={cn(
                          "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                          item.is_required
                            ? "bg-emerald-50 text-emerald-600"
                            : "bg-zinc-100 text-zinc-500",
                        )}
                      >
                        {item.is_required ? "필수" : "선택"}
                      </span>
                    </div>
                    {desc && (
                      <p className="mt-0.5 text-xs text-zinc-500">{desc}</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

/* -- 메인 컴포넌트 ----------------------------------------------------- */

type GroupedComposition = Record<CategoryKey, PMCompositionResponse[]>;

/**
 * Step 6: PM 구성 확인
 *
 * - GET /pm-profiles/{id}/composition 호출하여 5개 카테고리별 구성 요소 표시
 * - 각 카테고리는 접기/펴기 가능
 * - "이대로 진행" → 레이아웃의 다음 버튼 사용 (Step 7)
 * - "PM 재선택" → goToStep(4) (Step 5)
 */
export function StepPMComposition() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const selectedPmProfileId = useSolutionWizardStore(
    (s) => s.data.pm.selectedPmProfileId,
  );
  const recommendedItems = useSolutionWizardStore(
    (s) => s.data.pm.recommendedItems,
  );
  const setPM = useSolutionWizardStore((s) => s.setPM);
  const goToStep = useSolutionWizardStore((s) => s.goToStep);

  const [composition, setComposition] = useState<GroupedComposition | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const selectedPMInfo = recommendedItems.find(
    (i) => i.pmId === selectedPmProfileId,
  );

  /* -- 구성 요소 로드 -- */
  useEffect(() => {
    if (!selectedPmProfileId || !token) return;

    const loadComposition = async () => {
      setIsLoading(true);
      setFetchError(null);
      try {
        const [compData, profileData] = await Promise.all([
          pmProfiles.getComposition(token, selectedPmProfileId),
          pmProfiles.get(token, selectedPmProfileId),
        ]);
        setComposition({
          agents: compData.agents,
          skills: compData.skills,
          hooks: compData.hooks,
          mcp_servers: compData.mcp_servers,
          plugins: compData.plugins,
        });
        // 다음 스텝(플랫폼 선택)에서 PM 지원 플랫폼 필터링에 사용
        setPM({ pmSupportedPlatforms: profileData.supported_platforms ?? [] });
      } catch {
        setFetchError("PM 구성 정보를 불러오지 못했습니다.");
      } finally {
        setIsLoading(false);
      }
    };

    void loadComposition();
  }, [token, selectedPmProfileId, retryCount]);

  /* -- PM 미선택 ------------------------------------------------------- */
  if (!selectedPmProfileId) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <UserCircle2
          className="h-10 w-10 text-zinc-500"
          aria-hidden={true}
        />
        <p className="mt-4 text-sm text-zinc-500">선택된 PM이 없습니다.</p>
        <button
          type="button"
          onClick={() => goToStep(PM_SELECTION_STEP)}
          className="mt-4 flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-5 py-2.5 text-sm font-medium text-zinc-700 transition-all hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-950"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden={true} />
          PM 선택으로 돌아가기
        </button>
      </div>
    );
  }

  /* -- 로딩 ---------------------------------------------------------- */
  if (isLoading) {
    return (
      <div className="space-y-5">
        {/* PM 헤더 스켈레톤 */}
        <div className="flex animate-pulse items-center gap-3 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3">
          <div className="h-10 w-10 shrink-0 rounded-full bg-zinc-100" />
          <div className="space-y-1.5">
            <div className="h-3.5 w-28 rounded-md bg-zinc-100" />
            <div className="h-2.5 w-20 rounded-full bg-zinc-100" />
          </div>
        </div>
        <div className="flex items-center justify-center gap-2 py-8">
          <Loader2
            className="h-5 w-5 animate-spin text-emerald-600"
            aria-hidden={true}
          />
          <span className="text-sm text-zinc-500">구성 요소 불러오는 중...</span>
        </div>
      </div>
    );
  }

  /* -- 에러 ---------------------------------------------------------- */
  if (fetchError) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-rose-500/20 bg-rose-500/10">
          <AlertCircle
            className="h-6 w-6 text-rose-400"
            aria-hidden={true}
          />
        </div>
        <p className="mb-1 text-sm font-semibold text-rose-300">
          구성 정보 조회 실패
        </p>
        <p className="mb-6 text-xs text-zinc-500">{fetchError}</p>
        <button
          type="button"
          onClick={() => setRetryCount((c) => c + 1)}
          className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-5 py-2.5 text-sm font-medium text-zinc-700 transition-all hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-950"
        >
          <RefreshCw className="h-4 w-4" aria-hidden={true} />
          다시 시도
        </button>
      </div>
    );
  }

  /* -- 정상 상태 ------------------------------------------------------- */
  return (
    <div className="space-y-5">
      {/* PM 프로필 헤더 */}
      {selectedPMInfo && (
        <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-50">
            <UserCircle2
              className="h-5 w-5 text-emerald-600"
              aria-hidden={true}
            />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-zinc-950">
              {selectedPMInfo.name}
            </p>
            {selectedPMInfo.title && (
              <p className="text-xs text-zinc-500">{selectedPMInfo.title}</p>
            )}
          </div>
          {selectedPMInfo.matchScore > 0 && (
            <span className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
              일치율 {Math.round(selectedPMInfo.matchScore)}%
            </span>
          )}
        </div>
      )}

      {/* 구성 요소 섹션 */}
      {composition && (
        <div
          className="space-y-3"
          role="region"
          aria-label="PM 구성 요소 목록"
        >
          {CATEGORY_CONFIG.map(({ key, label, icon, color, bg, border }) => (
            <CompositionSection
              key={key}
              label={label}
              icon={icon}
              color={color}
              bg={bg}
              border={border}
              items={composition[key]}
            />
          ))}
        </div>
      )}

      {/* 다음 단계 안내 */}
      <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden={true} />
        <p className="text-xs text-zinc-600">
          이 PM의 기본 팀(에이전트·스킬·MCP·훅)이 다음 에이전트 구성 단계에서
          자동으로 선택됩니다. PM 팀 항목은 잠금 처리되며, 추가 항목은 자유롭게 선택할 수 있습니다.
        </p>
      </div>

      {/* PM 재선택 버튼 */}
      <div className="pt-2">
        <button
          type="button"
          onClick={() => goToStep(PM_SELECTION_STEP)}
          className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2 text-sm font-medium text-zinc-500 transition-all hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-700"
          aria-label="PM 선택 단계로 돌아가기"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden={true} />
          PM 재선택
        </button>
      </div>
    </div>
  );
}
