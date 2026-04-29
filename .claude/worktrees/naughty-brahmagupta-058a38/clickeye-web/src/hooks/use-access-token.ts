"use client";

import { useSession } from "next-auth/react";

/**
 * Next-Auth 세션에서 accessToken 문자열을 반환한다.
 * 세션이 없거나 토큰이 없으면 빈 문자열을 반환한다.
 */
export function useAccessToken(): string {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}
