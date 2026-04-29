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

// --- 프로토타입 생성 ---

export function useGeneratePrototypes(sessionId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => prototypeSessions.generatePrototypes(token, sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["prototype-sessions", sessionId, "status"],
      });
    },
  });
}

// --- PM 추천 ---

export function useRecommendPMs(sessionId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["prototype-sessions", sessionId, "recommend-pms"],
    queryFn: () => prototypeSessions.recommendPMs(token, sessionId),
    enabled: !!token && !!sessionId,
  });
}

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
