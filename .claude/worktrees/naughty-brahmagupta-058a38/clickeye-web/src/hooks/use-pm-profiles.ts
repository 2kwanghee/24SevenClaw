"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  pmProfiles,
  type PMRatingCreateRequest,
  type PMRecommendRequest,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

// --- 프로필 조회 ---

export function usePMProfiles(params?: {
  specialty?: string;
  domain?: string;
  is_active?: boolean;
  offset?: number;
  limit?: number;
}) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["pm-profiles", params],
    queryFn: () => pmProfiles.list(token, params),
    enabled: !!token,
  });
}

export function usePMProfile(profileId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["pm-profiles", profileId],
    queryFn: () => pmProfiles.get(token, profileId),
    enabled: !!token && !!profileId,
  });
}

// --- PM 구성 조회 ---

export function usePMComposition(profileId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["pm-profiles", profileId, "composition"],
    queryFn: () => pmProfiles.getComposition(token, profileId),
    enabled: !!token && !!profileId,
  });
}

// --- PM 추천 (프로토타입 기반) ---

export function useRecommendPMProfiles(data: PMRecommendRequest) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["pm-profiles", "recommend", data],
    queryFn: () => pmProfiles.recommend(token, data),
    enabled: !!token && !!data.prototype_id,
  });
}

// --- PM 평가 ---

export function usePMRatings(
  profileId: string,
  params?: { offset?: number; limit?: number },
) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["pm-profiles", profileId, "ratings", params],
    queryFn: () => pmProfiles.listRatings(token, profileId, params),
    enabled: !!token && !!profileId,
  });
}

export function useCreatePMRating(profileId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PMRatingCreateRequest) =>
      pmProfiles.createRating(token, profileId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["pm-profiles", profileId, "ratings"],
      });
      queryClient.invalidateQueries({
        queryKey: ["pm-profiles", profileId],
      });
    },
  });
}

// --- PM 메트릭 ---

export function usePMMetrics(profileId: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["pm-profiles", profileId, "metrics"],
    queryFn: () => pmProfiles.getMetrics(token, profileId),
    enabled: !!token && !!profileId,
  });
}
