"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { presets } from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function useMaturityQuestions() {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["maturity", "questions"],
    queryFn: () => presets.getQuestions(token),
    enabled: !!token,
  });
}

export function useSubmitAssessment() {
  const token = useAccessToken();

  return useMutation({
    mutationFn: (answers: Record<string, number>) =>
      presets.assess(token, answers),
  });
}
