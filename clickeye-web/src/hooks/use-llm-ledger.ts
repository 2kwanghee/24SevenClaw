"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { llmLedger } from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

/**
 * 프로젝트별 LLM 사용량 집계(토큰/비용) 조회.
 * 원장 엔드포인트는 settings:manage 권한이 필요하므로, 권한이 없으면
 * 호출 측에서 projectId를 비워(enabled=false) restricted 상태로 렌더한다.
 */
export function useLlmLedgerSummary(projectId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["llm-ledger-summary", projectId],
    queryFn: () => llmLedger.summary(token, projectId),
    enabled: !!token && !!projectId,
    staleTime: 60 * 1000,
  });
}
