"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { useAccessToken } from "@/hooks/use-access-token";

/**
 * 현재 로그인 사용자 정보(`/auth/me`)를 조회한다.
 * organization_id(소속 조직)와 system_role을 포함한다.
 */
export function useMe() {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => apiClient.auth.me(token),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });
}
