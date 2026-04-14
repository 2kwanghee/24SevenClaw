"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { presets, type PresetListParams } from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function usePresets(params?: PresetListParams) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["presets", params],
    queryFn: () => presets.list(token, params),
    enabled: !!token,
  });
}

export function usePreset(presetId: string) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["presets", presetId],
    queryFn: () => presets.get(token, presetId),
    enabled: !!token && !!presetId,
  });
}
