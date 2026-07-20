"use client";

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { ProjectList } from "@/components/projects/project-list";
import { ProjectListSkeleton } from "@/components/projects/project-list-skeleton";
import { useProjects } from "@/hooks/use-projects";

const PAGE_SIZE = 10;

type StatusFilter = "" | "active" | "archived";

function ProjectsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const tT = useTranslations("toast.projects");
  const t = useTranslations("projects.page");

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
      {/* 헤더 */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
        </div>
      </div>

      {/* 검색 + 필터 */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* 검색 */}
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder={t("searchPlaceholder")}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label={t("searchAria")}
            className="w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 pl-10 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>

        {/* 상태 필터 */}
        <div className="flex gap-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1">
          {([
            { value: "", label: t("filterAll") },
            { value: "active", label: t("filterActive") },
            { value: "archived", label: t("filterArchived") },
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
                  ? "bg-[var(--accent)] text-[var(--accent-fg)] shadow-sm"
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
          {t("loadError")}
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
            aria-label={t("prevPageAria")}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-muted)] transition-colors hover:border-[var(--border-medium)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map(
            (page) => (
              <button
                key={page}
                type="button"
                onClick={() => updateParams({ page: String(page) })}
                aria-label={t("pageAria", { page })}
                aria-current={page === currentPage ? "page" : undefined}
                className={`flex h-9 min-w-9 items-center justify-center rounded-lg px-2 text-sm font-medium transition-colors ${
                  page === currentPage
                    ? "bg-[var(--accent)] text-[var(--accent-fg)] shadow-sm"
                    : "border border-[var(--border-subtle)] text-[var(--text-muted)] hover:border-[var(--border-medium)] hover:text-[var(--text-primary)]"
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
            aria-label={t("nextPageAria")}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-subtle)] text-[var(--text-muted)] transition-colors hover:border-[var(--border-medium)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 결과 카운트 */}
      {data && (
        <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
          {t("totalCount", { count: data.total })}
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
