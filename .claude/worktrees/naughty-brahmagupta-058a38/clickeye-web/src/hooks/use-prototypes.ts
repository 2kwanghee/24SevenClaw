"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { prototypeSessions } from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

/** 세션의 프로토타입 목록 조회 */
export function usePrototypes(sessionId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["prototypes", sessionId],
    queryFn: () => prototypeSessions.getPrototypes(token, sessionId),
    enabled: !!token && !!sessionId,
  });
}
