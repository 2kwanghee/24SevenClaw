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
        <div className="mb-2 flex items-center justify-between text-xs text-[var(--text-muted)]">
          <span>
            {answeredCount}/{totalQuestions} 답변 완료
          </span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100">
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
                  "bg-violet-50 text-violet-600 ring-1 ring-violet-200",
                isDone && "bg-emerald-50 text-emerald-700",
                !isActive &&
                  !isDone &&
                  "bg-[var(--bg-hover)] text-[var(--text-muted)]",
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
          <Icon className="h-5 w-5 text-violet-600" />
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">{meta?.label}</h2>
          <span className="text-xs text-[var(--text-muted)]">
            {categoryIndex + 1}/{CATEGORY_ORDER.length}
          </span>
        </div>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">{meta?.description}</p>
      </div>

      {/* 질문 목록 */}
      <div className="space-y-6">
        {currentQuestions.map((q) => (
          <div
            key={q.id}
            className="animate-fade-in-up rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5"
          >
            <p className="mb-3 text-sm font-medium text-[var(--text-primary)]">{q.text}</p>
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
                        ? "border-violet-300 bg-violet-50 text-[var(--text-primary)]"
                        : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]",
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all",
                        isSelected
                          ? "border-violet-500 bg-violet-500"
                          : "border-[var(--border-medium)]",
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
              ? "cursor-not-allowed text-[var(--text-muted)]"
              : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]",
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
              ? "cursor-not-allowed bg-zinc-100 text-[var(--text-muted)]"
              : "bg-zinc-900 text-white shadow-lg hover:bg-zinc-800",
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
