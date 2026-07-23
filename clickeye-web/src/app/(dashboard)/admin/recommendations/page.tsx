"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { BarChart3, AlertCircle, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { BentoCard, BentoGrid } from "@/components/ui/bento";
import { RoleGuard } from "@/components/common/role-guard";
import { adminPMRecommendations, type PMRecommendationLogResponse } from "@/lib/api-client";

function RecommendationLogRow({ log }: { log: PMRecommendationLogResponse }) {
  const [expanded, setExpanded] = useState(false);
  const createdAt = log.created_at
    ? new Date(log.created_at).toLocaleString("ko-KR")
    : "—";

  const topPM = Array.isArray(log.final_ranking) && log.final_ranking.length > 0
    ? log.final_ranking[0]
    : null;

  return (
    <>
      <tr
        className="cursor-pointer border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-hover)]"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3 text-xs text-[var(--text-muted)] font-mono">
          {log.session_id.slice(0, 8)}…
        </td>
        <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">{createdAt}</td>
        <td className="px-4 py-3">
          {log.is_fallback ? (
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
              Fallback
            </span>
          ) : (
            <span className="rounded-full border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-2 py-0.5 text-xs text-[var(--text-secondary)]">
              Claude
            </span>
          )}
        </td>
        <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">
          {log.latency_ms != null ? `${log.latency_ms}ms` : "—"}
        </td>
        <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">
          {topPM ? `${String(topPM.pm_id).slice(0, 8)}… (${Math.round(Number(topPM.final_score))}점)` : "—"}
        </td>
        <td className="px-4 py-3">
          {log.selected_pm_id ? (
            <span className="text-xs text-[var(--text-secondary)] font-mono">
              {log.selected_pm_id.slice(0, 8)}…
            </span>
          ) : (
            <span className="text-xs text-[var(--text-muted)]">미선택</span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <td colSpan={6} className="px-4 py-4">
            <div className="space-y-3">
              <div>
                <p className="text-xs font-medium text-[var(--text-muted)] mb-1">입력 스냅샷</p>
                <pre className="text-xs text-[var(--text-muted)] overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(log.input_snapshot, null, 2)}
                </pre>
              </div>
              {log.final_ranking.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-[var(--text-muted)] mb-1">최종 순위</p>
                  <div className="space-y-1">
                    {log.final_ranking.slice(0, 5).map((r, i) => (
                      <div key={i} className="flex gap-3 text-xs text-[var(--text-muted)]">
                        <span className="text-[var(--text-muted)]">#{i + 1}</span>
                        <span className="font-mono">{String(r.pm_id).slice(0, 8)}…</span>
                        <span>최종: {Math.round(Number(r.final_score))}점</span>
                        <span className="text-[var(--text-muted)]">
                          (Claude: {Math.round(Number(r.claude_score))} / Rule: {Math.round(Number(r.rule_score))})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function RecommendationsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const [isFallbackFilter, setIsFallbackFilter] = useState<boolean | undefined>(undefined);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin-pm-recommendation-logs", isFallbackFilter],
    queryFn: () =>
      adminPMRecommendations.list(token, {
        is_fallback: isFallbackFilter,
        limit: 100,
      }),
    enabled: !!token,
  });

  const fallbackCount = data?.items.filter((l) => l.is_fallback).length ?? 0;
  const claudeCount = data?.items.filter((l) => !l.is_fallback).length ?? 0;
  const avgLatency = data && data.items.length > 0
    ? Math.round(
        data.items.reduce((sum, l) => sum + (l.latency_ms ?? 0), 0) /
          data.items.length,
      )
    : 0;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
            <BarChart3 className="h-5 w-5 text-[var(--accent)]" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[var(--text-primary)]">PM 추천 로그</h1>
            <p className="text-xs text-[var(--text-muted)]">Claude/Rule 추천 품질 모니터링</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] px-3 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)]"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          새로고침
        </button>
      </div>

      {/* 요약 카드 */}
      {data && (
        <BentoGrid className="lg:grid-cols-4">
          {[
            { label: "전체 추천", value: data.total, color: "text-[var(--text-primary)]" },
            { label: "Claude 기반", value: claudeCount, color: "text-[var(--text-secondary)]" },
            { label: "Fallback", value: fallbackCount, color: "text-amber-700" },
            { label: "평균 레이턴시", value: `${avgLatency}ms`, color: "text-[var(--text-secondary)]" },
          ].map((card) => (
            <BentoCard key={card.label} className="p-4">
              <p className="text-xs text-[var(--text-muted)]">{card.label}</p>
              <p className={`mt-1 text-xl font-semibold ${card.color}`}>{card.value}</p>
            </BentoCard>
          ))}
        </BentoGrid>
      )}

      {/* 필터 */}
      <div className="flex gap-2">
        {(
          [
            { label: "전체", value: undefined },
            { label: "Claude만", value: false },
            { label: "Fallback만", value: true },
          ] as { label: string; value: boolean | undefined }[]
        ).map((f) => (
          <button
            key={f.label}
            type="button"
            onClick={() => setIsFallbackFilter(f.value)}
            className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
              isFallbackFilter === f.value
                ? "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-secondary)]"
                : "border-[var(--border-subtle)] text-[var(--text-muted)] hover:bg-[var(--bg-hover)]"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && <div className="py-12 text-center text-sm text-[var(--text-muted)]">불러오는 중...</div>}
      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {(error as Error).message}
        </div>
      )}

      {data && (
        <BentoCard className="overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">세션 ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">생성 시각</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">추천 방식</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">레이턴시</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">1순위 PM</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">선택된 PM</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((log) => (
                <RecommendationLogRow key={log.id} log={log} />
              ))}
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-[var(--text-muted)]">
                    추천 로그가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </BentoCard>
      )}
    </div>
  );
}

export default function AdminRecommendationsPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <RecommendationsPage />
    </RoleGuard>
  );
}
