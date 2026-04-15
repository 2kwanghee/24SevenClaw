"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ClipboardList, ArrowRight } from "lucide-react";

import {
  useMaturityQuestions,
  useSubmitAssessment,
} from "@/hooks/use-maturity-assessment";
import { MaturityQuestionnaire } from "@/components/onboarding/maturity-questionnaire";
import { MaturityResult } from "@/components/onboarding/maturity-result";
import type { MaturityAssessmentResponse } from "@/lib/api-client";

export default function MaturityAssessmentPage() {
  const router = useRouter();
  const { data: questions, isLoading } = useMaturityQuestions();
  const submitMutation = useSubmitAssessment();
  const [result, setResult] = useState<MaturityAssessmentResponse | null>(null);

  const handleComplete = async (answers: Record<string, number>) => {
    const res = await submitMutation.mutateAsync(answers);
    setResult(res);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-violet-400" />
        <span className="ml-2 text-sm text-slate-400">
          질문 불러오는 중...
        </span>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      {/* 헤더 (질문지 모드에서만 표시) */}
      {!result && (
        <div className="mb-8">
          <div className="mb-1 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-violet-400" />
            <h1 className="text-2xl font-bold text-white">성숙도 평가</h1>
          </div>
          <p className="text-sm text-slate-400">
            팀의 개발 성숙도를 평가하고 최적의 프리셋을 추천받으세요
          </p>
          <button
            type="button"
            onClick={() => router.push("/projects/new")}
            className="mt-2 flex items-center gap-1 text-xs text-slate-500 transition-colors hover:text-slate-300"
          >
            건너뛰고 직접 설정하기
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      )}

      {result ? (
        <div className="mt-8">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold text-white">평가 결과</h1>
            <p className="mt-1 text-sm text-slate-400">
              팀의 AI 개발 성숙도를 분석했습니다
            </p>
          </div>
          <MaturityResult result={result} />
        </div>
      ) : questions && questions.length > 0 ? (
        <MaturityQuestionnaire
          questions={questions}
          onComplete={handleComplete}
          isSubmitting={submitMutation.isPending}
        />
      ) : (
        <div className="rounded-xl border border-white/5 bg-white/[0.02] px-6 py-12 text-center">
          <p className="text-sm text-slate-500">
            질문을 불러올 수 없습니다. 나중에 다시 시도하세요.
          </p>
          <button
            type="button"
            onClick={() => router.push("/projects/new")}
            className="mt-4 text-sm text-violet-400 hover:text-violet-300"
          >
            위저드로 이동
          </button>
        </div>
      )}
    </div>
  );
}
