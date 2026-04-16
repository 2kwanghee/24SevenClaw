"use client";

import { AlertCircle, Sparkles } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { PrototypeCard } from "../prototype-card";

/**
 * Step 3: 프로토타입 선택
 *
 * 이 컴포넌트는 순수 선택 UI입니다.
 * 프로토타입 생성/폴링은 이전 단계(StepPrototypeGeneration)에서 처리됩니다.
 */
export function StepPrototypes() {
  const prototypes = useSolutionWizardStore((s) => s.data.prototypes);
  const selectPrototype = useSolutionWizardStore((s) => s.selectPrototype);

  /* ── 빈 상태 (생성된 프로토타입 없음) ──────────────────────────────── */
  if (prototypes.generatedPrototypes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <AlertCircle className="h-10 w-10 text-slate-600" aria-hidden="true" />
        <p className="mt-4 text-sm font-medium text-slate-400">
          생성된 프로토타입이 없습니다
        </p>
        <p className="mt-1 text-xs text-slate-500">
          이전 단계로 돌아가 정보를 다시 확인해 주세요.
        </p>
      </div>
    );
  }

  /* ── 프로토타입 카드 목록 ──────────────────────────────────────────── */
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400">
        <Sparkles
          className="mr-1 inline-block h-3.5 w-3.5 text-emerald-400"
          aria-hidden="true"
        />
        AI가 분석한 솔루션 후보입니다. 가장 적합한 방향을 선택하세요.
      </p>
      <div className="space-y-3" role="list" aria-label="솔루션 프로토타입 목록">
        {prototypes.generatedPrototypes.map((proto) => (
          <PrototypeCard
            key={proto.id}
            prototype={proto}
            isSelected={prototypes.selectedPrototypeId === proto.id}
            onSelect={selectPrototype}
          />
        ))}
      </div>
    </div>
  );
}
