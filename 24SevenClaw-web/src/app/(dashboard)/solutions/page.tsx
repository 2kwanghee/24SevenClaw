"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  Sparkles,
  Plus,
  Loader2,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";

import { prototypeSessions, ApiClientError } from "@/lib/api-client";
import type { PrototypeSessionResponse } from "@/lib/api-client";

const STATUS_CONFIG: Record<
  PrototypeSessionResponse["status"],
  { label: string; icon: typeof CheckCircle2; className: string }
> = {
  completed: {
    label: "완료",
    icon: CheckCircle2,
    className: "text-emerald-400",
  },
  generating: {
    label: "생성 중",
    icon: Loader2,
    className: "animate-spin text-yellow-400",
  },
  pending: {
    label: "대기 중",
    icon: Clock,
    className: "text-slate-400",
  },
  failed: {
    label: "실패",
    icon: XCircle,
    className: "text-red-400",
  },
};

export default function SolutionsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const [sessions, setSessions] = useState<PrototypeSessionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;

    const fetchSessions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await prototypeSessions.list(token, { limit: 20 });
        setSessions(Array.isArray(result) ? result : []);
      } catch (err) {
        if (err instanceof ApiClientError) {
          setError(err.detail);
        } else {
          setError("세션 목록을 불러오지 못했습니다.");
        }
      } finally {
        setIsLoading(false);
      }
    };

    void fetchSessions();
  }, [token]);

  return (
    <div className="mx-auto max-w-3xl">
      {/* 헤더 */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">솔루션 위저드</h1>
          <p className="mt-1 text-sm text-slate-400">
            AI가 회사에 맞는 솔루션을 자동 설계합니다
          </p>
        </div>
        <Link
          href="/solutions/new"
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-600/25 transition-colors hover:bg-emerald-500"
          aria-label="새 솔루션 위저드 시작"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          새 솔루션
        </Link>
      </div>

      {/* Hero card */}
      <div className="mb-8 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10">
            <Sparkles className="h-6 w-6 text-emerald-400" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-white">
              7단계 위저드로 AI 솔루션 설계
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              회사 정보를 입력하면 AI가 맞춤 프로토타입을 생성하고, PM 추천부터
              에이전트 구성, 플랫폼 선택까지 자동으로 안내합니다.
            </p>
            <Link
              href="/solutions/new"
              className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-emerald-400 transition-colors hover:text-emerald-300"
            >
              지금 시작하기
              <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </div>

      {/* 최근 세션 */}
      <section aria-labelledby="recent-sessions-heading">
        <h2
          id="recent-sessions-heading"
          className="mb-4 text-sm font-semibold text-slate-300"
        >
          최근 세션
        </h2>

        {isLoading && (
          <div
            className="flex items-center justify-center py-12"
            role="status"
            aria-label="세션 목록 로딩 중"
          >
            <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
            <span className="sr-only">세션 목록을 불러오고 있습니다...</span>
          </div>
        )}

        {!isLoading && error && (
          <div
            role="alert"
            className="flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3"
          >
            <AlertCircle className="h-4 w-4 shrink-0 text-red-400" aria-hidden="true" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {!isLoading && !error && sessions.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-white/5 bg-white/[0.02] py-16 text-center">
            <Sparkles className="h-10 w-10 text-slate-600" aria-hidden="true" />
            <p className="mt-4 text-sm text-slate-400">아직 세션이 없습니다</p>
            <p className="mt-1 text-xs text-slate-500">
              새 솔루션 위저드를 시작해 보세요
            </p>
            <Link
              href="/solutions/new"
              className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-300 transition-colors hover:bg-emerald-500/20"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              새 솔루션 시작
            </Link>
          </div>
        )}

        {!isLoading && !error && sessions.length > 0 && (
          <ul className="space-y-2" role="list" aria-label="최근 솔루션 세션 목록">
            {sessions.map((s) => {
              const cfg = STATUS_CONFIG[s.status];
              const Icon = cfg.icon;
              const companyName = s.solution_prompt
                ? s.solution_prompt.slice(0, 40) + (s.solution_prompt.length > 40 ? "..." : "")
                : "—";
              const solutionRequest = s.solution_prompt ?? "";
              const createdAt = new Date(s.created_at).toLocaleDateString(
                "ko-KR",
                { year: "numeric", month: "short", day: "numeric" },
              );

              return (
                <li key={s.id}>
                  <Link
                    href={`/solutions/${s.id}`}
                    className="flex items-center gap-4 rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3 transition-colors hover:border-white/10 hover:bg-white/[0.04]"
                    aria-label={`${companyName} 세션 열기`}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/5">
                      <Sparkles className="h-4 w-4 text-emerald-400" aria-hidden="true" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white">
                        {companyName}
                      </p>
                      {solutionRequest && (
                        <p className="mt-0.5 truncate text-xs text-slate-500">
                          {solutionRequest.length > 80
                            ? solutionRequest.slice(0, 80) + "..."
                            : solutionRequest}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs text-slate-500">{createdAt}</span>
                      <div className="flex items-center gap-1.5">
                        <Icon
                          className={`h-3.5 w-3.5 ${cfg.className}`}
                          aria-hidden="true"
                        />
                        <span className="text-xs text-slate-400">
                          {cfg.label}
                        </span>
                      </div>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
