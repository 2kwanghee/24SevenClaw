"use client";

import Link from "next/link";
import { Boxes, Loader2, AlertTriangle, ChevronRight } from "lucide-react";

import { useProjects } from "@/hooks/use-projects";
import { MockModeToggle } from "@/components/delivery/mock-mode-toggle";
import { useMockMode } from "@/stores/mock-mode-store";
import { mockProject } from "@/lib/delivery-mock";

export default function DeliveryListPage() {
  const mock = useMockMode((s) => s.enabled);
  const { data, isLoading: isLoadingRaw, isError: isErrorRaw } = useProjects();

  const engagements = mock ? [mockProject] : data?.items ?? [];
  const isLoading = mock ? false : isLoadingRaw;
  const isError = mock ? false : isErrorRaw;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)] text-[var(--accent-fg)]">
          <Boxes className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            딜리버리
          </h1>
          <p className="text-xs text-[var(--text-muted)]">
            수주건별 SI 딜리버리 관제
          </p>
        </div>
        <div className="ml-auto">
          <MockModeToggle />
        </div>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--text-muted)]" aria-hidden="true" />
        </div>
      )}

      {/* 에러 */}
      {isError && !isLoading && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          수주건 목록을 불러오지 못했습니다.
        </div>
      )}

      {/* 빈 상태 */}
      {!isLoading && !isError && engagements.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--bg-hover)]">
            <Boxes className="h-7 w-7 text-[var(--text-muted)]" aria-hidden="true" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            아직 등록된 수주건이 없습니다
          </p>
          <Link
            href="/projects"
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90"
          >
            프로젝트에서 시작하기
          </Link>
        </div>
      )}

      {/* 수주건 목록 */}
      {!isLoading && !isError && engagements.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {engagements.map((engagement) => (
            <Link
              key={engagement.id}
              href={`/delivery/${engagement.id}`}
              className="group flex items-start gap-3 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-[0_1px_2px_rgba(20,24,33,0.05)] transition-colors hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
                <Boxes className="h-4.5 w-4.5 text-[var(--text-muted)]" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="truncate text-sm font-semibold text-[var(--text-primary)]">
                    {engagement.name}
                  </h2>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      engagement.status === "active"
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                        : "bg-[var(--bg-hover)] text-[var(--text-muted)]"
                    }`}
                  >
                    {engagement.status === "active" ? "진행 중" : "보관됨"}
                  </span>
                </div>
                {engagement.description && (
                  <p className="mt-1 line-clamp-2 text-xs text-[var(--text-muted)]">
                    {engagement.description}
                  </p>
                )}
              </div>
              <ChevronRight className="h-4 w-4 shrink-0 text-[var(--text-muted)] transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
