"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { appSettingsAdmin } from "@/lib/api-client";

export function useAppSettings() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  return useQuery({
    queryKey: ["app-settings"],
    queryFn: () => appSettingsAdmin.getAll(token),
    enabled: !!token,
  });
}

export function useSetVariantCount() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (value: number) => appSettingsAdmin.setVariantCount(token, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["app-settings"] }),
  });
}

export function useSetRagTopK() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (value: number) => appSettingsAdmin.setRagTopK(token, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["app-settings"] }),
  });
}

