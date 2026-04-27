"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  roiAdmin,
  type RoiStandardCreateRequest,
  type RoiStandardUpdateRequest,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function useRoiStandards(category?: string) {
  const token = useAccessToken();
  return useQuery({
    queryKey: ["roi-standards", category],
    queryFn: () => roiAdmin.list(token, category, true),
    enabled: !!token,
  });
}

export function useCreateRoiStandard() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RoiStandardCreateRequest) => roiAdmin.create(token, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["roi-standards"] }),
  });
}

export function useUpdateRoiStandard() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RoiStandardUpdateRequest }) =>
      roiAdmin.update(token, id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["roi-standards"] }),
  });
}

export function useDeleteRoiStandard() {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => roiAdmin.delete(token, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["roi-standards"] }),
  });
}
