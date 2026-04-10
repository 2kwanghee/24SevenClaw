"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  apiClient,
  type ProjectCreateRequest,
  type ProjectListParams,
  type ProjectUpdateRequest,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function useProjects(params?: ProjectListParams) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["projects", params],
    queryFn: () => apiClient.projects.list(token, params),
    enabled: !!token,
  });
}

export function useProject(projectId: string) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => apiClient.projects.get(token, projectId),
    enabled: !!token && !!projectId,
  });
}

export function useCreateProject() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreateRequest) =>
      apiClient.projects.create(token, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useUpdateProject(projectId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectUpdateRequest) =>
      apiClient.projects.update(token, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useDeleteProject() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) =>
      apiClient.projects.delete(token, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
