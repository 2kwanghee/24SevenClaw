"use client";

import { useQuery } from "@tanstack/react-query";

import { governance } from "@/lib/api-client";
import { useAccessToken } from "@/hooks/use-access-token";

/**
 * 머지 게이트 거버넌스 정책을 조회한다.
 * GET /api/v1/governance/policy — 인증 필요(토큰 없으면 비활성).
 */
export function useGovernancePolicy(enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["governance", "policy"],
    queryFn: () => governance.getPolicy(token),
    enabled: enabled && !!token,
    staleTime: 5 * 60 * 1000,
  });
}
