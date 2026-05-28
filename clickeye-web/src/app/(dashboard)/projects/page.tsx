"use client";

import Link from "next/link";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Plus, Search, ChevronLeft, ChevronRight, Sparkles, ArrowRight, GitBranch } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { ProjectList } from "@/components/projects/project-list";
import { ProjectListSkeleton } from "@/components/projects/project-list-skeleton";
import { useProjects } from "@/hooks/use-projects";
import { isModernizeEnabled } from "@/lib/feature-flags";

const PAGE_SIZE = 10;

type StatusFilter = "" | "active" | "archived";

function ProjectsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const tT = useTranslations("toast.projects");

  // URL searchParams에서 상태 추출
  const currentPage = Math.max(1, Number(searchParams.get("page") ?? "1"));
  const searchQuery = searchParams.get("search") ?? "";
  const statusFilter = (searchParams.get("status") ?? "") as StatusFilter;

  // 검색 입력용 로컬 상태 (debounce)
  const [searchInput, setSearchInput] = useState(searchQuery);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  // URL 업데이트 헬퍼
  const updateParams = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value) {
          params.set(key, value);
        } else {
          params.delete(key);
        }
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [searchParams, router, pathname],
  );

  // 검색 debounce (300ms)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (searchInput !== searchQuery) {
        updateParams({ search: searchInput, page: "" });
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchInput, searchQuery, updateParams]);

  // URL search가 변경되면 input 동기화
  useEffect(() => {
    setSearchInput(searchQuery);
  }, [searchQuery]);

  const offset = (currentPage - 1) * PAGE_SIZE;

  const { data, isLoading, error } = useProjects({
    offset,
    limit: PAGE_SIZE,
    search: searchQuery || undefined,
    status: statusFilter || undefined,
  });

  useEffect(() => {
    if (error) {
      toast.error(tT("fetchFail"));
    }
  }, [error, tT]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      {/* 새 솔루션 위저드 CTA 배너 */}
      <div className="mb-8 flex flex-col gap-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
            <Sparkles className="h-5 w-5 text-[var(--text-secondary)]" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">새 솔루션 위저드</p>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              직접 AI 솔루션을 설계하고 ZIP으로 바로 시작하세요
            </p>
          </div>
        </div>
        <Link
          href="/solutions/new"
          className="flex shrink-0 items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white transition-all hover:bg-zinc-800"
          aria-label="새 솔루션 위저드 시작"
        >
          솔루션 설계 시작
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>

      {/* Modernize 진입 카드 (FEATURE_MODERNIZE_ENABLED=true 인 베타 사용자만 노출) */}
      {isModernizeEnabled() && (
        <div className="mb-8 flex flex-col gap-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50">
              <GitBranch className="h-5 w-5 text-amber-700" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[var(--text-primary)]">
                기존 코드 현대화 <span className="ml-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">BETA</span>
              </p>
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                GitHub 저장소를 연결하면 AI가 코드를 진단하고 현대화 작업을 Linear에 자동 등록합니다
              </p>
            </div>
          </div>
          <Link
            href="/solutions/modernize/new"
            className="flex shrink-0 items-center gap-2 rounded-xl border border-zinc-900 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-900 transition-all hover:bg-zinc-50"
            aria-label="기존 코드 현대화 위저드 시작"
          >
            저장소 연결하기
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      )}

      {/* 헤더 */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">프로젝트</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            AI 에이전트가 작업할 프로젝트를 관리하세요
          </p>
        </div>
      </div>

      {/* 검색 + 필터 */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* 검색 */}
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="프로젝트 검색..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label="프로젝트 검색"
            className="w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 pl-10 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-zinc-400 focus:ring-1 focus:ring-zinc-300"
          />
        </div>

        {/* 상태 필터 */}
        <div className="flex gap-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1">
          {([
            { value: "", label: "전체" },
            { value: "active", label: "활성" },
            { value: "archived", label: "보관됨" },
          ] as const).map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() =>
                updateParams({ status: option.value, page: "" })
              }
              aria-pressed={statusFilter === option.value}
              className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors ${
                statusFilter === option.value
                  ? "bg-zinc-900 text-white shadow-sm"
                  : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* 로딩 (스켈레톤) */}
      {isLoading && <ProjectListSkeleton />}

      {/* 에러 */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          프로젝트 목록을 불러오지 못했습니다.
        </div>
      )}

      {/* 목록 */}
      {data && <ProjectList projects={data.items} />}

      {/* 페이지네이션 */}
      {data && data.total > PAGE_SIZE && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() =>
              updateParams({ page: String(currentPage - 1) })
            }
            aria-label="이전 페이지"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-muted)] transition-colors hover:border-zinc-400 hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map(
            (page) => (
              <button
                key={page}
                type="button"
                onClick={() => updateParams({ page: String(page) })}
                aria-label={`${page}페이지`}
                aria-current={page === currentPage ? "page" : undefined}
                className={`flex h-9 min-w-9 items-center justify-center rounded-lg px-2 text-sm font-medium transition-colors ${
                  page === currentPage
                    ? "bg-zinc-900 text-white shadow-sm"
                    : "border border-[var(--border-subtle)] text-[var(--text-muted)] hover:border-zinc-400 hover:text-[var(--text-primary)]"
                }`}
              >
                {page}
              </button>
            ),
          )}

          <button
            type="button"
            disabled={currentPage >= totalPages}
            onClick={() =>
              updateParams({ page: String(currentPage + 1) })
            }
            aria-label="다음 페이지"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-muted)] transition-colors hover:border-zinc-400 hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 결과 카운트 */}
      {data && (
        <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
          총 {data.total}개 프로젝트
        </p>
      )}
    </div>
  );
}

export default function ProjectsPage() {
  return (
    <Suspense fallback={<ProjectListSkeleton />}>
      <ProjectsContent />
    </Suspense>
  );
}
