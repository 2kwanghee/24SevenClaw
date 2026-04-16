"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  orchestrator,
  reviews,
  type MergeStrategy,
  type OrchestratorPhase,
  type SubTaskRole,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

// --- Sessions ---

export function useSessionList(projectId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["orchestrator-sessions", projectId],
    queryFn: () => orchestrator.listSessions(token, projectId, { limit: 50 }),
    enabled: !!token && !!projectId,
  });
}

export function useSessionSummary(sessionId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["orchestrator-summary", sessionId],
    queryFn: () => orchestrator.getSessionSummary(token, sessionId),
    enabled: !!token && !!sessionId,
    refetchInterval: 30_000,
  });
}

export function useCreateSession(projectId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { title: string; description?: string }) =>
      orchestrator.createSession(token, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["orchestrator-sessions", projectId],
      });
    },
  });
}

export function useDecompose() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      hints,
    }: {
      sessionId: string;
      hints?: string[];
    }) => orchestrator.decompose(token, sessionId, hints),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: ["orchestrator-summary", vars.sessionId],
      });
    },
  });
}

export function useAssign() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      overrides,
    }: {
      sessionId: string;
      overrides?: Record<string, SubTaskRole>;
    }) => orchestrator.assign(token, sessionId, overrides),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: ["orchestrator-summary", vars.sessionId],
      });
    },
  });
}

export function useTransition() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sessionId,
      targetPhase,
      message,
    }: {
      sessionId: string;
      targetPhase: OrchestratorPhase;
      message?: string;
    }) => orchestrator.transition(token, sessionId, targetPhase, message),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: ["orchestrator-summary", vars.sessionId],
      });
    },
  });
}

// --- Reviews ---

export function useReviewRounds(sessionId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["review-rounds", sessionId],
    queryFn: () => reviews.list(token, sessionId, { limit: 50 }),
    enabled: !!token && !!sessionId,
    refetchInterval: 30_000,
  });
}

export function useReviewDiff(roundId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["review-diff", roundId],
    queryFn: () => reviews.getDiff(token, roundId),
    enabled: !!token && !!roundId,
  });
}

export function useMergeReview() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      roundId,
      mergeStrategy,
      mergedContent,
      message,
    }: {
      roundId: string;
      mergeStrategy: MergeStrategy;
      mergedContent?: string;
      message?: string;
    }) =>
      reviews.merge(token, roundId, {
        merge_strategy: mergeStrategy,
        merged_content: mergedContent,
        message,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-rounds"] });
      queryClient.invalidateQueries({ queryKey: ["orchestrator-summary"] });
    },
  });
}

export function useRejectReview() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ roundId, reason }: { roundId: string; reason: string }) =>
      reviews.reject(token, roundId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-rounds"] });
      queryClient.invalidateQueries({ queryKey: ["orchestrator-summary"] });
    },
  });
}
