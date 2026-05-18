"use client";

import {
  AlertCircle,
  CheckCircle2,
  Download,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { useState } from "react";
import { useSession } from "next-auth/react";

import { modernize } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { cn } from "@/lib/utils";

/**
 * Step 4 (Modernize) — 최종 확인 + finalize.
 *
 * 사용자가 "Linear 등록 + ZIP 다운로드" 버튼을 누르면:
 *   1. POST /modernize/sessions/{id}/finalize
 *   2. 응답의 zip_url 로 브라우저 navigate (다운로드)
 *   3. parent Linear URL + N 건 등록 결과를 노출
 */
export function StepModernizeConfirm() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const sessionId = useSolutionWizardStore((s) => s.modernize.sessionId);
  const scenario = useSolutionWizardStore((s) => s.modernize.scenario);
  const acceptedIds = useSolutionWizardStore(
    (s) => s.modernize.acceptedRecommendationIds,
  );
  const repo = useSolutionWizardStore((s) => s.modernize.repo);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    linear_parent_url: string | null;
    linear_parent_identifier: string | null;
    linear_child_count: number;
    linear_errors: string[];
    zip_url: string;
    selected_recommendation_count: number;
  } | null>(null);

  const handleFinalize = async (withLinear: boolean) => {
    if (!token || !sessionId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await modernize.finalizeSession(token, sessionId, {
        create_linear_issues: withLinear,
      });
      setResult(res);
      // ZIP 다운로드 자동 트리거 (인증 헤더가 필요하므로 fetch + blob)
      await downloadZip(token, sessionId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "finalize 실패");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4" role="region" aria-label="최종 확인">
      {/* 요약 카드 */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <h3 className="mb-3 text-sm font-medium text-zinc-700">설정 요약</h3>
        <dl className="space-y-1.5 text-sm">
          <SummaryRow label="저장소" value={repo?.fullName ?? "-"} />
          <SummaryRow label="브랜치" value={repo?.branch ?? "-"} />
          <SummaryRow
            label="시나리오"
            value={scenario ? scenario : "-"}
          />
          <SummaryRow
            label="선택한 권장사항"
            value={`${acceptedIds.length} 건`}
          />
        </dl>
      </div>

      {/* 액션 */}
      {!result && (
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => void handleFinalize(true)}
            disabled={busy || acceptedIds.length === 0}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition-all",
              busy || acceptedIds.length === 0
                ? "cursor-not-allowed bg-zinc-200 text-zinc-400"
                : "bg-zinc-900 text-white hover:bg-zinc-800",
            )}
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Linear 자동 등록 + ZIP 다운로드
          </button>
          <button
            type="button"
            onClick={() => void handleFinalize(false)}
            disabled={busy || acceptedIds.length === 0}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm font-medium text-zinc-700 transition-all hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ZIP 만 다운로드 (Linear 등록 건너뜀)
          </button>
          {acceptedIds.length === 0 && (
            <p className="text-xs text-amber-600">
              권장사항을 1건 이상 선택해야 진행할 수 있습니다.
            </p>
          )}
        </div>
      )}

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            <div className="flex-1 text-sm text-emerald-800">
              <p className="font-medium">완료</p>
              <p className="mt-0.5 text-xs">
                ZIP {result.zip_url ? "다운로드 시작됨" : "준비됨"}
                {result.linear_child_count > 0
                  ? ` · Linear ${result.linear_child_count}건 등록`
                  : ""}
                {result.linear_errors.length > 0
                  ? ` · 실패 ${result.linear_errors.length}건`
                  : ""}
              </p>
            </div>
          </div>

          {result.linear_parent_url && (
            <a
              href={result.linear_parent_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-zinc-700 hover:text-zinc-900"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Linear 부모 이슈 열기
              {result.linear_parent_identifier && (
                <span className="font-mono text-xs text-zinc-500">
                  ({result.linear_parent_identifier})
                </span>
              )}
            </a>
          )}

          <button
            type="button"
            onClick={() => sessionId && downloadZip(token, sessionId)}
            className="flex items-center gap-2 text-sm text-zinc-700 hover:text-zinc-900"
          >
            <Download className="h-3.5 w-3.5" />
            ZIP 다시 다운로드
          </button>
        </div>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-3">
      <dt className="w-24 shrink-0 text-xs text-zinc-500">{label}</dt>
      <dd className="font-medium text-zinc-900">{value}</dd>
    </div>
  );
}

async function downloadZip(token: string, sessionId: string): Promise<void> {
  const url =
    (process.env.NEXT_PUBLIC_API_URL ?? "") +
    modernize.zipDownloadUrl(sessionId);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`ZIP 다운로드 실패 (${res.status})`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = `modernize_${sessionId}.zip`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}
