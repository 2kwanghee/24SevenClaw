"use client";

import { useEffect, useRef } from "react";
import { useSession } from "next-auth/react";

import { wizardPreview } from "@/lib/api-client";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import type { SolutionWizardStepId } from "@/types/solution-wizard";

const DEBOUNCE_MS = 700;

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

/**
 * 위자드 라이브 프리뷰 훅.
 * 현재 step의 입력이 DEBOUNCE_MS 동안 안정되면 /wizard/preview를 호출하고
 * 결과를 store에 저장한다. 빠른 입력 시 이전 요청은 abort된다.
 */
export function useWizardPreview(
  stepId: SolutionWizardStepId,
  inputData: Record<string, unknown>,
  /** 프리뷰를 호출하기에 충분한 입력이 있는지 판단하는 함수 */
  isReady: (data: Record<string, unknown>) => boolean,
) {
  const token = useAccessToken();
  const { setPreview, setPreviewLoading, setPreviewError } = useSolutionWizardStore();

  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 마지막으로 요청한 입력의 직렬화값 — 동일 입력 재요청 방지
  const lastInputRef = useRef<string>("");

  const inputJson = JSON.stringify(inputData);

  useEffect(() => {
    if (!token) return;
    if (!isReady(inputData)) return;
    if (inputJson === lastInputRef.current) return;

    // 이전 타이머 취소
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      // 이전 진행 중인 요청 abort
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      lastInputRef.current = inputJson;
      setPreviewLoading(stepId);

      try {
        const res = await wizardPreview.fetch(token, { step: stepId, data: inputData });
        if (controller.signal.aborted) return;

        if (res.supported && res.result) {
          setPreview(stepId, res.result);
        } else {
          setPreviewError(stepId, null);
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        const msg = err instanceof Error ? err.message : "프리뷰를 불러오지 못했습니다";
        setPreviewError(stepId, msg);
      } finally {
        if (!controller.signal.aborted) {
          setPreviewLoading(null);
        }
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  // inputJson 변경 시에만 재실행
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputJson, token]);
}
