"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  prototypeSessions,
  type FinalizeRequest,
  type PrototypeSessionCreateRequest,
  type PrototypeSessionUpdateRequest,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

// --- 세션 조회 ---

export function usePrototypeSessions(params?: { offset?: number; limit?: number }) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["prototype-sessions", params],
    queryFn: () => prototypeSessions.list(token, params),
    enabled: !!token,
  });
}

export function usePrototypeSession(sessionId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["prototype-sessions", sessionId],
    queryFn: () => prototypeSessions.get(token, sessionId),
    enabled: !!token && !!sessionId,
  });
}

export function usePrototypeSessionStatus(sessionId: string, enabled = true) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["prototype-sessions", sessionId, "status"],
    queryFn: () => prototypeSessions.getStatus(token, sessionId),
    enabled: !!token && !!sessionId && enabled,
    refetchInterval: (data) => {
      // generating/pending 상태면 2초마다 폴링
      if (data?.state.data?.status === "generating" || data?.state.data?.status === "pending") {
        return 2000;
      }
      return false;
    },
  });
}

// --- 세션 생성/수정 ---

export function useCreatePrototypeSession() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PrototypeSessionCreateRequest) =>
      prototypeSessions.create(token, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prototype-sessions"] });
    },
  });
}

export function useUpdatePrototypeSession(sessionId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PrototypeSessionUpdateRequest) =>
      prototypeSessions.update(token, sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prototype-sessions", sessionId] });
    },
  });
}

// 참고: 프로토타입 생성·PM 추천(LLM POST)은 useQuery/useMutation 훅을 쓰지 않는다.
// useQuery로 POST를 감싸면 refetchOnWindowFocus/stale 재요청으로 LLM 호출이 중복된다.
// 각 위저드 스텝 컴포넌트가 sessionId 키 ref 가드로 정확히 1회만 직접 호출한다.

// --- 세션 확정 (프로젝트 생성) ---

export function useFinalizeSession(sessionId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FinalizeRequest) =>
      prototypeSessions.finalize(token, sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prototype-sessions"] });
    },
  });
}

// --- 세션 삭제 ---

export function useDeletePrototypeSession() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => prototypeSessions.delete(token, sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prototype-sessions"] });
    },
  });
}
