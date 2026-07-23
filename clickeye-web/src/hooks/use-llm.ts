"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { llm, type LlmFeedbackPayload } from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

/**
 * 딜리버리 LLM 어시스턴트 RAG Q&A.
 * delivery_id = projectId 로 매핑되어 clickeye-api → clickeye-llm 으로 프록시된다.
 * clickeye-llm 미가용 시 503(LLM_UNAVAILABLE) 으로 degrade → 호출 측에서 안내 처리.
 */
export function useLlmChat(projectId: string) {
  const token = useAccessToken();
  return useMutation({
    mutationFn: (query: string) => llm.chat(token, projectId, query),
  });
}

/**
 * 챗 답변 피드백 제출(👍/👎 + 선택 코멘트, P2-MVP).
 * 성공 시 {feedback_id} — 호출 측에서 버튼 비활성 + 감사 문구 처리.
 */
export function useSendLlmFeedback(projectId: string) {
  const token = useAccessToken();
  return useMutation({
    mutationFn: (payload: LlmFeedbackPayload) =>
      llm.feedback(token, projectId, payload),
  });
}

/**
 * 축적 지식 기반 진행상황 요약.
 * 버튼 클릭 등으로 명시적으로 트리거하기 위해 기본 enabled=false 로 둔다.
 */
export function useLlmProgress(projectId: string, enabled: boolean) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["llm-progress", projectId],
    queryFn: () => llm.progress(token, projectId),
    enabled: !!token && !!projectId && enabled,
    staleTime: 30 * 1000,
    retry: false,
  });
}
