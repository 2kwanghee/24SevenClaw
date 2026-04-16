"use client";

import { Loader2, Sparkles, CheckCircle2, ChevronRight } from "lucide-react";
import { useEffect } from "react";
import { useSession } from "next-auth/react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { prototypeSessions } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const SOLUTION_TYPE_LABELS: Record<string, string> = {
  saas: "SaaS",
  "rest-api": "REST API",
  fullstack: "풀스택 웹",
  "internal-tool": "내부 도구",
  mvp: "MVP",
  custom: "커스텀",
};

export function StepPrototypes() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const sessionId = useSolutionWizardStore((s) => s.data.sessionId);
  const prototypes = useSolutionWizardStore((s) => s.data.prototypes);
  const isGenerating = useSolutionWizardStore((s) => s.isGenerating);
  const selectPrototype = useSolutionWizardStore((s) => s.selectPrototype);
  const setGeneratedPrototypes = useSolutionWizardStore(
    (s) => s.setGeneratedPrototypes,
  );
  const setIsGenerating = useSolutionWizardStore((s) => s.setIsGenerating);

  // 세션이 있고 프로토타입이 없으면 자동 생성
  useEffect(() => {
    if (!sessionId || !token) return;
    if (prototypes.generatedPrototypes.length > 0) return;

    const generate = async () => {
      setIsGenerating(true);
      try {
        const result = await prototypeSessions.generate(token, sessionId);
        setGeneratedPrototypes(
          result.map((p) => ({
            id: p.id,
            name: p.name,
            solutionType: p.solution_type,
            reasoning: p.reasoning,
            config: p.config,
          })),
        );
      } catch {
        // 생성 실패 시 무시 (빈 목록 유지)
      } finally {
        setIsGenerating(false);
      }
    };

    void generate();
  }, [
    sessionId,
    token,
    prototypes.generatedPrototypes.length,
    setGeneratedPrototypes,
    setIsGenerating,
  ]);

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="h-10 w-10 animate-spin text-emerald-400" />
        <p className="mt-4 text-sm font-medium text-white">
          AI가 솔루션 후보를 생성하고 있습니다...
        </p>
        <p className="mt-1 text-xs text-slate-500">
          입력하신 정보를 분석하여 최적의 솔루션을 설계 중입니다
        </p>
      </div>
    );
  }

  if (prototypes.generatedPrototypes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Sparkles className="h-10 w-10 text-slate-600" />
        <p className="mt-4 text-sm text-slate-400">
          프로토타입을 생성할 수 없습니다
        </p>
        <p className="mt-1 text-xs text-slate-500">
          이전 단계로 돌아가 정보를 다시 확인해 주세요
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400">
        AI가 분석한 솔루션 후보입니다. 가장 적합한 방향을 선택하세요.
      </p>
      <div className="space-y-3">
        {prototypes.generatedPrototypes.map((proto) => {
          const isSelected = prototypes.selectedPrototypeId === proto.id;
          return (
            <button
              key={proto.id}
              type="button"
              onClick={() => selectPrototype(proto.id)}
              aria-pressed={isSelected}
              className={cn(
                "group w-full rounded-xl border p-4 text-left transition-all duration-200",
                isSelected
                  ? "border-emerald-500/50 bg-emerald-500/10 ring-2 ring-emerald-500/20"
                  : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">
                      {proto.name}
                    </span>
                    <span className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-slate-400">
                      {SOLUTION_TYPE_LABELS[proto.solutionType] ??
                        proto.solutionType}
                    </span>
                  </div>
                  {proto.reasoning && (
                    <p className="text-xs leading-relaxed text-slate-400">
                      {proto.reasoning}
                    </p>
                  )}
                </div>
                {isSelected ? (
                  <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
                ) : (
                  <ChevronRight className="h-5 w-5 shrink-0 text-slate-600 transition-colors group-hover:text-slate-400" />
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
