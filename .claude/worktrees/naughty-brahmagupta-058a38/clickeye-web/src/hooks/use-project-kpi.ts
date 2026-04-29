"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { apiClient } from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function useProjectKPI(projectId: string) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["project-kpi", projectId],
    queryFn: () => apiClient.projects.kpi(token, projectId),
    enabled: !!token && !!projectId,
    staleTime: 30_000,
  });
}
