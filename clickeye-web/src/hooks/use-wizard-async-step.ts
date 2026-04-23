"use client";

import { useCallback, useEffect, useRef } from "react";

interface UseWizardAsyncStepOptions<K> {
  /** 이 값이 바뀌면 실행 가드가 리셋되어 재실행이 허용된다 (예: sessionId). */
  key: K;
  /** 비동기 작업 본체. AbortSignal로 취소 여부를 확인할 수 있다. */
  run: (signal: AbortSignal) => Promise<void>;
  /** false면 실행하지 않는다 (토큰·sessionId가 준비되지 않은 경우 등). */
  enabled?: boolean;
}

/**
 * 위저드 비동기 Step의 단일 실행을 보장하는 훅.
 *
 * - React StrictMode 이중 마운트 환경에서도 `run`이 1회만 호출된다.
 * - `key`가 변경되면 실행 가드가 리셋되어 `run`이 다시 허용된다.
 * - 컴포넌트 언마운트 시 AbortController.abort()를 호출해 진행 중 작업에 힌트를 전달한다.
 */
export function useWizardAsyncStep<K>({
  key,
  run,
  enabled = true,
}: UseWizardAsyncStepOptions<K>): void {
  const startedForKey = useRef<K | symbol>(Symbol("uninit"));
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(() => {
    if (!enabled) return;
    if (startedForKey.current === key) return;
    startedForKey.current = key;

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    void run(ctrl.signal);
  }, [enabled, key, run]);

  useEffect(() => {
    start();
    return () => {
      abortRef.current?.abort();
    };
  }, [start]);
}
