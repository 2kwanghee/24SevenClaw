"use client";

import { CheckCircle2, ExternalLink, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { modernize, type ModernizeInstallationItem } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

/**
 * Step 0 (Modernize) — GitHub App 설치/연결.
 *
 * 흐름:
 *   1. 마운트 시 GET /modernize/installations 로 기존 활성 installation 조회
 *   2. 1개 이상 존재 → 자동으로 첫 installation 선택 + canProceed 트리거
 *   3. 0개 → "GitHub 연결" 버튼 노출, 클릭 시 popup 으로 /install-url 의 URL 열기
 *   4. popup 에서 GitHub UI 진행 → ClickEye callback → /solutions/modernize/connected 페이지
 *      가 부모창에 postMessage 또는 setInterval refetch 로 알림 (MVP: 5초 polling)
 *   5. 새 installation 감지 → store.modernize.githubInstallationPk 갱신
 */
export function StepModernizeRepoConnect() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const modernizeState = useSolutionWizardStore((s) => s.modernize);
  const setModernize = useSolutionWizardStore((s) => s.setModernize);

  const [installations, setInstallations] = useState<ModernizeInstallationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInstallations = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const items = await modernize.listInstallations(token);
      setInstallations(items);
      // 첫 활성 installation 자동 선택
      if (items.length > 0 && !modernizeState.githubInstallationPk) {
        setModernize({
          githubInstallationPk: items[0].id,
          githubInstallationId: items[0].installation_id,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "설치 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [token, modernizeState.githubInstallationPk, setModernize]);

  useEffect(() => {
    void fetchInstallations();
  }, [fetchInstallations]);

  // popup 진행 중 polling — 5초마다 refetch
  useEffect(() => {
    if (!installing) return;
    const id = setInterval(() => {
      void fetchInstallations();
    }, 5000);
    return () => clearInterval(id);
  }, [installing, fetchInstallations]);

  const handleConnect = async () => {
    if (!token) return;
    setInstalling(true);
    setError(null);
    try {
      const { install_url, state } = await modernize.installUrl(token);
      // state 는 callback 에서 검증됨. install_url 에 query string 으로 붙임
      const url = `${install_url}?state=${encodeURIComponent(state)}`;
      // popup 으로 열기 (사용자가 닫거나 콜백 후 자동 닫힘은 GitHub 측 정책)
      window.open(url, "github-app-install", "width=900,height=700");
    } catch (e) {
      setError(e instanceof Error ? e.message : "설치 URL 발급 실패");
      setInstalling(false);
    }
  };

  const selectedInstallation = installations.find(
    (i) => i.id === modernizeState.githubInstallationPk,
  );

  return (
    <div className="space-y-4" role="region" aria-label="GitHub 연결">
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-6">
        <h3 className="mb-2 text-base font-semibold text-zinc-900">
          GitHub 저장소 연결
        </h3>
        <p className="mb-4 text-sm text-zinc-600">
          ClickEye Modernize 는 GitHub App 으로 private repo 에 안전하게 접근합니다.
          최소 권한(Contents read, Metadata read)만 요청합니다.
        </p>

        {loading && (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            installation 조회 중...
          </div>
        )}

        {!loading && installations.length === 0 && (
          <button
            type="button"
            onClick={handleConnect}
            disabled={installing}
            className="flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-50"
          >
            <ExternalLink className="h-4 w-4" />
            {installing ? "GitHub 설치 대기 중..." : "GitHub 연결"}
          </button>
        )}

        {!loading && installations.length > 0 && selectedInstallation && (
          <div className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-zinc-900">
                {selectedInstallation.account_login}{" "}
                <span className="text-xs text-zinc-500">
                  ({selectedInstallation.account_type})
                </span>
              </p>
              <p className="text-xs text-zinc-500">
                저장소 {selectedInstallation.repo_count}개 · 권한:{" "}
                {selectedInstallation.repository_selection === "all"
                  ? "전체"
                  : "선택"}
              </p>
            </div>
            <button
              type="button"
              onClick={handleConnect}
              className="rounded-md px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-zinc-100"
            >
              다른 계정으로 연결
            </button>
          </div>
        )}

        {error && (
          <p role="alert" className="mt-3 text-xs text-red-600">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
