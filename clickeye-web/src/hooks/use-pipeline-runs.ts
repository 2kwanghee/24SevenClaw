"use client";

import { useQuery } from "@tanstack/react-query";

import { pipelineRuns } from "@/lib/api-client";
import { useAccessToken } from "@/hooks/use-access-token";

interface UsePipelineRunsParams {
  issueKey?: string;
  projectId?: string;
  limit?: number;
  offset?: number;
}

/**
 * 무인 체인 파이프라인 실행 이력 조회(CE-363/364).
 *
 * 엔드포인트는 settings:manage 권한 전용이라, 권한 없는 사용자는 403 을 받는다.
 * 원장 훅(use-llm-ledger)과 동일하게 훅 자체는 상태를 판정하지 않고, 호출 측이
 * RBAC 로 restricted 를 계산해 enabled=false 로 쿼리를 비활성화한다(불필요한 403 방지).
 */
export function usePipelineRuns(
  params: UsePipelineRunsParams,
  enabled = true,
) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["pipeline-runs", params],
    queryFn: () => pipelineRuns.list(token, params),
    enabled: !!token && enabled,
    staleTime: 60 * 1000,
  });
}
