"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ClipboardList, ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  useMaturityQuestions,
  useSubmitAssessment,
} from "@/hooks/use-maturity-assessment";
import { MaturityQuestionnaire } from "@/components/onboarding/maturity-questionnaire";
import { MaturityResult } from "@/components/onboarding/maturity-result";
import type { MaturityAssessmentResponse } from "@/lib/api-client";

export default function MaturityAssessmentPage() {
  const router = useRouter();
  const t = useTranslations("onboarding.maturity");
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
        <Loader2 className="h-6 w-6 animate-spin text-zinc-700" />
        <span className="ml-2 text-sm text-[var(--text-muted)]">{t("loadingQuestions")}</span>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      {/* 헤더 (질문지 모드에서만 표시) */}
      {!result && (
        <div className="mb-8">
          <div className="mb-1 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-zinc-700" />
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
          </div>
          <p className="text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
          <button
            type="button"
            onClick={() => router.push("/delivery")}
            className="mt-2 flex items-center gap-1 text-xs text-[var(--text-muted)] transition-colors hover:text-[var(--text-secondary)]"
          >
            {t("skipBtn")}
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      )}

      {result ? (
        <div className="mt-8">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("resultTitle")}</h1>
            <p className="mt-1 text-sm text-[var(--text-muted)]">{t("resultSubtitle")}</p>
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
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 py-12 text-center">
          <p className="text-sm text-[var(--text-muted)]">{t("questionsError")}</p>
          <button
            type="button"
            onClick={() => router.push("/delivery")}
            className="mt-4 text-sm text-zinc-700 hover:text-[var(--text-primary)]"
          >
            {t("goToWizard")}
          </button>
        </div>
      )}
    </div>
  );
}
