"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  pmProfiles,
  type PMCompositionCreateRequest,
  type PMCompositionUpdateRequest,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

type UpsertArgs =
  | { id?: undefined; data: PMCompositionCreateRequest }
  | { id: string; data: PMCompositionUpdateRequest };

export function useUpsertComposition(profileId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (args: UpsertArgs) => {
      if (args.id) {
        return pmProfiles.updateComposition(
          token,
          profileId,
          args.id,
          args.data as PMCompositionUpdateRequest,
        );
      }
      return pmProfiles.createComposition(
        token,
        profileId,
        args.data as PMCompositionCreateRequest,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["pm-composition", profileId],
      });
    },
  });
}

export function useDeleteComposition(profileId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (compositionId: string) =>
      pmProfiles.deleteComposition(token, profileId, compositionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["pm-composition", profileId],
      });
    },
  });
}
