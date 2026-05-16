"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { AlertCircle, Sparkles, LayoutGrid, Columns3 } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { prototypeSessions } from "@/lib/api-client";
import { PrototypeCard } from "../prototype-card";
import { PrototypeComparisonTable } from "@/components/prototypes/prototype-comparison-table";
import { cn } from "@/lib/utils";

/**
 * Step 3: 프로토타입 선택 (API 연동 버전)
 *
 * - 카드 모드: 카드 클릭 → 선택 하이라이트 + 프리뷰 확대
 * - 비교 모드: 표 형태로 정량 지표 차별점 비교 (Phase B)
 * - 선택 시 PATCH /prototype-sessions/{id} (selected_prototype_id) 호출
 */
export function StepPrototypeSelection() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const prototypes = useSolutionWizardStore((s) => s.data.prototypes);
  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);
  const selectPrototype = useSolutionWizardStore((s) => s.selectPrototype);

  const [expandedId, setExpandedId] = useState<string | null>(
    prototypes.selectedPrototypeId,
  );
  const [viewMode, setViewMode] = useState<"cards" | "compare">("cards");

  const handleSelect = (prototypeId: string) => {
    selectPrototype(prototypeId);
    setExpandedId(prototypeId);

    // 낙관적 업데이트: UI는 즉시 반영, API는 fire-and-forget
    if (sessionId && token) {
      void prototypeSessions
        .update(token, sessionId, { selected_prototype_id: prototypeId })
        .catch(() => {
          // 실패해도 UI 상태는 유지 (다음 단계 진행은 로컬 상태로 제어)
        });
    }
  };

  /* -- 빈 상태 ----------------------------------------------------------- */
  if (prototypes.generatedPrototypes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertCircle className="h-10 w-10 text-zinc-500" aria-hidden="true" />
        <p className="mt-4 text-sm font-medium text-zinc-500">
          생성된 프로토타입이 없습니다
        </p>
        <p className="mt-1 text-xs text-zinc-500">
          이전 단계로 돌아가 정보를 다시 확인해 주세요.
        </p>
      </div>
    );
  }

  /* -- 프로토타입 카드 목록 ---------------------------------------------- */
  return (
    <div className="space-y-4">
      {/* 안내 + 보기 모드 토글 */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-zinc-500">
          <Sparkles
            className="mr-1 inline-block h-3.5 w-3.5 text-emerald-600"
            aria-hidden="true"
          />
          AI가 분석한 솔루션 후보입니다. 가장 적합한 방향을 선택하세요.
        </p>
        <div className="inline-flex shrink-0 rounded-lg border border-zinc-200 bg-white p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("cards")}
            aria-pressed={viewMode === "cards"}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
              viewMode === "cards"
                ? "bg-zinc-900 text-white"
                : "text-zinc-600 hover:bg-zinc-50",
            )}
          >
            <LayoutGrid className="h-3 w-3" />
            카드
          </button>
          <button
            type="button"
            onClick={() => setViewMode("compare")}
            aria-pressed={viewMode === "compare"}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
              viewMode === "compare"
                ? "bg-zinc-900 text-white"
                : "text-zinc-600 hover:bg-zinc-50",
            )}
          >
            <Columns3 className="h-3 w-3" />
            비교
          </button>
        </div>
      </div>

      {viewMode === "cards" ? (
        <div className="space-y-3" role="list" aria-label="솔루션 프로토타입 목록">
          {prototypes.generatedPrototypes.map((proto) => (
            <PrototypeCard
              key={proto.id}
              prototype={proto}
              isSelected={prototypes.selectedPrototypeId === proto.id}
              isExpanded={expandedId === proto.id}
              onSelect={handleSelect}
            />
          ))}
        </div>
      ) : (
        <PrototypeComparisonTable
          prototypes={prototypes.generatedPrototypes}
          selectedId={prototypes.selectedPrototypeId}
          onSelect={handleSelect}
        />
      )}
    </div>
  );
}
