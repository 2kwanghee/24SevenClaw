"use client";

import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";

import { modernize, type ModernizeSessionResponse } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { cn } from "@/lib/utils";

/**
 * Step 2 (Modernize) — 자동 진행 + 진행률 폴링.
 *
 * 흐름:
 *   1. 마운트 시 modernize.sessionId 없으면 POST /modernize/sessions 호출
 *   2. session 생성 후 3초 간격으로 GET /sessions/{id} 폴링
 *   3. status='ready' 도달 → store.modernize.diagnoseDone=true → 부모가 nextStep 트리거
 *   4. status='failed' 도달 → 에러 표시 + 재시도 버튼
 *
 * 시나리오 입력은 M5 시점에서는 'versionup' default. M6 에서 diagnosis-review step 의
 * 사용자 입력으로 분기 예정.
 */

const POLL_INTERVAL_MS = 3000;

const STEP_LABELS: Array<{ label: string; threshold: number }> = [
  { label: "저장소 클론", threshold: 15 },
  { label: "언어/프레임워크 감지", threshold: 35 },
  { label: "의존성 분석", threshold: 55 },
  { label: "Outdated 검사", threshold: 70 },
  { label: "코드 샘플링", threshold: 80 },
  { label: "AI 요약", threshold: 95 },
  { label: "완료", threshold: 100 },
];

export function StepModernizeDiagnose() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const installationPk = useSolutionWizardStore(
    (s) => s.modernize.githubInstallationPk,
  );
  const repo = useSolutionWizardStore((s) => s.modernize.repo);
  const sessionId = useSolutionWizardStore((s) => s.modernize.sessionId);
  const scenarioFromStore = useSolutionWizardStore((s) => s.modernize.scenario);
  const setModernize = useSolutionWizardStore((s) => s.setModernize);

  const [sessionState, setSessionState] = useState<ModernizeSessionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const didStartRef = useRef(false);

  const startSession = useCallback(async () => {
    if (!token || !installationPk || !repo) {
      setError("Github 연결 또는 저장소 선택이 누락되었습니다. 이전 단계로 돌아가세요.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const res = await modernize.createSession(token, {
        installation_pk: installationPk,
        repo_full_name: repo.fullName,
        branch: repo.branch,
        // M5 단계: scenario 기본값 'versionup'. M6 에서 diagnosis-review 단계가 사용자 선택을 반영.
        scenario: scenarioFromStore ?? "versionup",
      });
      setSessionState(res);
      setModernize({ sessionId: res.id });
    } catch (e) {
      setError(e instanceof Error ? e.message : "분석 세션 생성 실패");
    } finally {
      setCreating(false);
    }
  }, [token, installationPk, repo, scenarioFromStore, setModernize]);

  // 1회 자동 시작
  useEffect(() => {
    if (didStartRef.current) return;
    if (sessionId) {
      // 이미 세션이 있으면 폴링만 시작 (페이지 새로고침 케이스)
      didStartRef.current = true;
      return;
    }
    didStartRef.current = true;
    void startSession();
  }, [sessionId, startSession]);

  // 폴링
  useEffect(() => {
    const id = sessionState?.id ?? sessionId;
    if (!id || !token) return;
    if (sessionState?.status === "ready" || sessionState?.status === "failed") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const res = await modernize.getSession(token, id);
        setSessionState(res);
        if (res.status === "ready") {
          setModernize({ diagnoseDone: true });
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "상태 조회 실패");
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [sessionState?.id, sessionState?.status, sessionId, token, setModernize]);

  const progress = sessionState?.progress_pct ?? 0;
  const isFailed = sessionState?.status === "failed";
  const isReady = sessionState?.status === "ready";

  const handleRetry = () => {
    didStartRef.current = false;
    setSessionState(null);
    setModernize({ sessionId: null, diagnoseDone: false });
    void startSession();
  };

  return (
    <div className="space-y-4" role="region" aria-label="코드 진단">
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-6">
        <h3 className="mb-2 text-base font-semibold text-zinc-900">
          {repo?.fullName ?? "저장소"} 분석 중
        </h3>
        <p className="mb-4 text-sm text-zinc-600">
          AI 가 저장소를 클론·스캔하고 의존성 + 코드 구조를 분석합니다. 보통 30~90초 소요됩니다.
        </p>

        {/* 진행률 바 */}
        <div className="mb-4 h-2 w-full overflow-hidden rounded-full bg-zinc-200">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              isFailed ? "bg-red-500" : "bg-zinc-900",
            )}
            style={{ width: `${progress}%` }}
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        <p className="mb-4 text-xs text-zinc-500">{progress}% 완료</p>

        {/* 단계 체크리스트 */}
        <ul className="space-y-2 text-sm">
          {STEP_LABELS.map((step, i) => {
            const isDone = progress >= step.threshold;
            const isCurrent = !isDone && (i === 0 || progress >= STEP_LABELS[i - 1].threshold);
            return (
              <li key={step.label} className="flex items-center gap-2">
                {isDone ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : isCurrent && !isFailed ? (
                  <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
                ) : (
                  <div className="h-4 w-4 rounded-full border border-zinc-300" />
                )}
                <span
                  className={cn(
                    isDone ? "text-zinc-900" : "text-zinc-500",
                    isCurrent && !isDone && "font-medium",
                  )}
                >
                  {step.label}
                </span>
              </li>
            );
          })}
        </ul>

        {creating && (
          <p className="mt-4 text-xs text-zinc-500">분석 세션을 생성하는 중...</p>
        )}

        {isFailed && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
            <div className="mb-2 flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
              <p className="text-sm font-medium text-red-700">분석 실패</p>
            </div>
            <p className="text-xs text-red-600">
              {(sessionState?.error?.message as string | undefined) ??
                "알 수 없는 오류가 발생했습니다."}
            </p>
            <button
              type="button"
              onClick={handleRetry}
              className="mt-3 flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-red-500"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              다시 시도
            </button>
          </div>
        )}

        {isReady && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            <p className="text-sm text-emerald-700">
              분석 완료. 다음 단계에서 권장사항을 검토하세요.
            </p>
          </div>
        )}

        {error && !isFailed && (
          <p role="alert" className="mt-3 text-xs text-red-600">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
