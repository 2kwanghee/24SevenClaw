"use client";

import { useState, useCallback } from "react";
import {
  Users,
  GitBranch,
  Wrench,
  Rocket,
  Bot,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { MaturityQuestion } from "@/lib/api-client";

const CATEGORY_META: Record<
  string,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    description: string;
  }
> = {
  team: {
    label: "팀 역량",
    icon: Users,
    description: "팀 규모와 AI 경험 수준을 알려주세요",
  },
  process: {
    label: "개발 프로세스",
    icon: GitBranch,
    description: "코드 리뷰와 브랜치 전략을 확인합니다",
  },
  tooling: {
    label: "개발 도구",
    icon: Wrench,
    description: "IDE와 테스트 자동화 수준을 파악합니다",
  },
  ci: {
    label: "CI/CD",
    icon: Rocket,
    description: "파이프라인과 배포 주기를 확인합니다",
  },
  ai: {
    label: "AI 활용",
    icon: Bot,
    description: "AI 도구 활용과 품질 관리 체계를 평가합니다",
  },
};

const CATEGORY_ORDER = ["team", "process", "tooling", "ci", "ai"];

interface MaturityQuestionnaireProps {
  questions: MaturityQuestion[];
  onComplete: (answers: Record<string, number>) => void;
  isSubmitting: boolean;
}

export function MaturityQuestionnaire({
  questions,
  onComplete,
  isSubmitting,
}: MaturityQuestionnaireProps) {
  const [categoryIndex, setCategoryIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});

  const questionsByCategory = CATEGORY_ORDER.reduce<
    Record<string, MaturityQuestion[]>
  >((acc, cat) => {
    acc[cat] = questions.filter((q) => q.category === cat);
    return acc;
  }, {});

  const currentCategory = CATEGORY_ORDER[categoryIndex];
  const currentQuestions = questionsByCategory[currentCategory] ?? [];
  const meta = CATEGORY_META[currentCategory];
  const Icon = meta?.icon ?? Bot;
  const isLastCategory = categoryIndex === CATEGORY_ORDER.length - 1;

  const allCurrentAnswered = currentQuestions.every(
    (q) => answers[q.id] !== undefined,
  );
  const totalQuestions = questions.length;
  const answeredCount = Object.keys(answers).length;
  const progress =
    totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;

  const handleSelect = useCallback((questionId: string, score: number) => {
    setAnswers((prev) => ({ ...prev, [questionId]: score }));
  }, []);

  const handleNext = () => {
    if (isLastCategory) {
      onComplete(answers);
    } else {
      setCategoryIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    setCategoryIndex((prev) => Math.max(0, prev - 1));
  };

  return (
    <div>
      {/* 진행률 바 */}
      <div className="mb-8">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
          <span>
            {answeredCount}/{totalQuestions} 답변 완료
          </span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
          <div
            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* 카테고리 인디케이터 */}
      <div className="mb-6 flex items-center gap-3">
        {CATEGORY_ORDER.map((cat, idx) => {
          const CatIcon = CATEGORY_META[cat]?.icon ?? Bot;
          const isActive = idx === categoryIndex;
          const isDone = idx < categoryIndex;
          return (
            <button
              key={cat}
              type="button"
              onClick={() => idx <= categoryIndex && setCategoryIndex(idx)}
              disabled={idx > categoryIndex}
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-lg transition-all",
                isActive &&
                  "bg-violet-500/20 text-violet-400 ring-1 ring-violet-500/30",
                isDone && "bg-emerald-500/10 text-emerald-400",
                !isActive &&
                  !isDone &&
                  "bg-white/[0.03] text-slate-600",
              )}
              title={CATEGORY_META[cat]?.label}
              aria-label={CATEGORY_META[cat]?.label}
            >
              {isDone ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <CatIcon className="h-4 w-4" />
              )}
            </button>
          );
        })}
      </div>

      {/* 카테고리 헤더 */}
      <div className="mb-6">
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-semibold text-white">{meta?.label}</h2>
          <span className="text-xs text-slate-600">
            {categoryIndex + 1}/{CATEGORY_ORDER.length}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-400">{meta?.description}</p>
      </div>

      {/* 질문 목록 */}
      <div className="space-y-6">
        {currentQuestions.map((q) => (
          <div
            key={q.id}
            className="animate-fade-in-up rounded-2xl border border-white/5 bg-white/[0.02] p-5"
          >
            <p className="mb-3 text-sm font-medium text-slate-200">{q.text}</p>
            <div className="space-y-2">
              {q.options.map((opt) => {
                const isSelected = answers[q.id] === opt.score;
                return (
                  <button
                    key={opt.label}
                    type="button"
                    onClick={() => handleSelect(q.id, opt.score)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition-all",
                      isSelected
                        ? "border-violet-500/40 bg-violet-500/10 text-white"
                        : "border-white/5 bg-white/[0.01] text-slate-400 hover:border-white/10 hover:bg-white/[0.03] hover:text-slate-200",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all",
                        isSelected
                          ? "border-violet-400 bg-violet-400"
                          : "border-slate-600",
                      )}
                      aria-hidden="true"
                    >
                      {isSelected && (
                        <span className="h-2 w-2 rounded-full bg-white" />
                      )}
                    </span>
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 네비게이션 버튼 */}
      <div className="mt-8 flex items-center justify-between">
        <button
          type="button"
          onClick={handlePrev}
          disabled={categoryIndex === 0}
          className={cn(
            "flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all",
            categoryIndex === 0
              ? "cursor-not-allowed text-slate-600"
              : "text-slate-400 hover:bg-white/5 hover:text-white",
          )}
        >
          <ArrowLeft className="h-4 w-4" />
          이전
        </button>

        <button
          type="button"
          onClick={handleNext}
          disabled={!allCurrentAnswered || isSubmitting}
          className={cn(
            "group flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
            !allCurrentAnswered || isSubmitting
              ? "cursor-not-allowed bg-violet-600/30 text-violet-300/50"
              : "bg-violet-600 text-white shadow-lg shadow-violet-600/25 hover:bg-violet-500",
          )}
        >
          {isSubmitting
            ? "분석 중..."
            : isLastCategory
              ? "결과 확인"
              : "다음"}
          {!isSubmitting && (
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          )}
        </button>
      </div>
    </div>
  );
}
