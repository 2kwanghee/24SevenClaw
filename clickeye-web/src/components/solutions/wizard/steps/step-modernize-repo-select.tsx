"use client";

import { GitBranch, Loader2, Lock, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { modernize, type ModernizeRepoItem } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { cn } from "@/lib/utils";

/**
 * Step 1 (Modernize) — repo + branch 선택.
 *
 * `modernize.githubInstallationPk` 가 설정된 후에 접근. installation 의 repo 목록을
 * GET /modernize/installations/{id}/repos 로 조회하고 사용자 선택을 store 에 반영.
 */
export function StepModernizeRepoSelect() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const installationPk = useSolutionWizardStore(
    (s) => s.modernize.githubInstallationPk,
  );
  const repo = useSolutionWizardStore((s) => s.modernize.repo);
  const setModernize = useSolutionWizardStore((s) => s.setModernize);

  const [repos, setRepos] = useState<ModernizeRepoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRepos = useCallback(
    async (refresh = false) => {
      if (!token || !installationPk) return;
      const setBusy = refresh ? setRefreshing : setLoading;
      setBusy(true);
      setError(null);
      try {
        const items = await modernize.listRepos(token, installationPk, refresh);
        setRepos(items);
      } catch (e) {
        setError(e instanceof Error ? e.message : "저장소 목록을 불러오지 못했습니다.");
      } finally {
        setBusy(false);
      }
    },
    [token, installationPk],
  );

  useEffect(() => {
    void fetchRepos(false);
  }, [fetchRepos]);

  if (!installationPk) {
    return (
      <p className="text-sm text-zinc-500">
        먼저 GitHub 계정을 연결하세요.
      </p>
    );
  }

  return (
    <div className="space-y-4" role="region" aria-label="저장소 선택">
      <div className="flex items-center justify-between">
        <p className="text-sm text-zinc-600">분석할 저장소와 브랜치를 선택하세요.</p>
        <button
          type="button"
          onClick={() => void fetchRepos(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-100 disabled:opacity-50"
          aria-label="저장소 목록 새로고침"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
          새로고침
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          저장소 목록 조회 중...
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {!loading && repos.length === 0 && !error && (
        <p className="text-sm text-zinc-500">
          접근 가능한 저장소가 없습니다. GitHub App 설치 단계에서 repo 를 선택했는지 확인하세요.
        </p>
      )}

      {!loading && repos.length > 0 && (
        <ul className="max-h-96 space-y-1 overflow-y-auto rounded-xl border border-zinc-200 p-2">
          {repos.map((r) => {
            const isSelected = repo?.fullName === r.full_name;
            return (
              <li key={r.gh_repo_id}>
                <button
                  type="button"
                  onClick={() =>
                    setModernize({
                      repo: {
                        fullName: r.full_name,
                        branch: r.default_branch,
                        subpath: null,
                      },
                    })
                  }
                  aria-pressed={isSelected}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                    isSelected
                      ? "border border-zinc-900 bg-zinc-50 ring-2 ring-zinc-900/10"
                      : "border border-transparent hover:bg-zinc-50",
                  )}
                >
                  {r.private && <Lock className="h-3.5 w-3.5 shrink-0 text-amber-500" aria-label="private" />}
                  <span className="flex-1 font-medium text-zinc-900">{r.full_name}</span>
                  {r.language_primary && (
                    <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-600">
                      {r.language_primary}
                    </span>
                  )}
                  <span className="flex items-center gap-1 text-xs text-zinc-500">
                    <GitBranch className="h-3 w-3" />
                    {r.default_branch}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {repo && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <p className="text-xs font-medium text-emerald-700">선택됨</p>
          <p className="mt-1 text-sm font-medium text-zinc-900">
            {repo.fullName}
            <span className="ml-2 text-xs text-zinc-500">
              <GitBranch className="mr-0.5 inline h-3 w-3" />
              {repo.branch}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
