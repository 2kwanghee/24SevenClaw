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

const AUTO_PROGRESS_PHASES = new Set(["drafting", "reviewing", "integrating", "approved", "transitioning"]);

export function useSessionSummary(sessionId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["orchestrator-summary", sessionId],
    queryFn: () => orchestrator.getSessionSummary(token, sessionId),
    enabled: !!token && !!sessionId,
    refetchInterval: ({ state }) => {
      const phase = (state.data as { session?: { phase?: string } } | undefined)?.session?.phase;
      return phase && AUTO_PROGRESS_PHASES.has(phase) ? 3_000 : 30_000;
    },
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

export function useDeleteSession(projectId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      orchestrator.deleteSession(token, sessionId),
    onSuccess: (_data, sessionId) => {
      // 목록 캐시에서 즉시 제거 (낙관적 업데이트)
      queryClient.setQueryData<{ items: Array<{ id: string }> }>(
        ["orchestrator-sessions", projectId],
        (old) => {
          if (!old) return old;
          return { ...old, items: old.items.filter((s) => s.id !== sessionId) };
        },
      );
      // 삭제된 세션의 summary/review 캐시를 즉시 제거
      queryClient.removeQueries({ queryKey: ["orchestrator-summary", sessionId] });
      queryClient.removeQueries({ queryKey: ["review-rounds", sessionId] });
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

export function useGenerateDrafts() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId }: { sessionId: string }) =>
      reviews.generateDrafts(token, sessionId),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: ["orchestrator-summary", vars.sessionId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["review-rounds", vars.sessionId],
      });
    },
  });
}

export function usePushToLinear() {
  const token = useAccessToken();
  return useMutation({
    mutationFn: ({ sessionId }: { sessionId: string }) =>
      reviews.pushToLinear(token, sessionId),
  });
}

export function useApproveSubtask() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, subtaskId }: { sessionId: string; subtaskId: string }) =>
      reviews.approveSubtask(token, sessionId, subtaskId),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: ["orchestrator-summary", vars.sessionId],
      });
    },
  });
}

// --- Reviews ---

export function useReviewRounds(sessionId: string, fastPoll = false) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["review-rounds", sessionId],
    queryFn: () => reviews.list(token, sessionId, { limit: 50 }),
    enabled: !!token && !!sessionId,
    refetchInterval: fastPoll ? 3_000 : 30_000,
  });
}

export function useResumePipeline() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId }: { sessionId: string }) =>
      reviews.resumePipeline(token, sessionId),
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({
        queryKey: ["orchestrator-summary", vars.sessionId],
      });
    },
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
