"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  registryAgents,
  registrySkills,
  registryMcpServers,
  type RegistryItemCreateRequest,
  type RegistryItemUpdateRequest,
  type RegistryListParams,
} from "@/lib/api-client";

export type RegistryAdminType = "agents" | "skills" | "mcps";

const clientMap = {
  agents: registryAgents,
  skills: registrySkills,
  mcps: registryMcpServers,
} as const;

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function useRegistryItems(type: RegistryAdminType, params?: RegistryListParams) {
  const token = useAccessToken();
  const client = clientMap[type];
  return useQuery({
    queryKey: ["registry-admin", type, params],
    queryFn: () => client.list(token, { limit: 200, ...params }),
    enabled: !!token,
  });
}

export function useCreateRegistryItem(type: RegistryAdminType) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  const client = clientMap[type];
  return useMutation({
    mutationFn: (data: RegistryItemCreateRequest) => client.create(token, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["registry-admin", type] }),
  });
}

export function useUpdateRegistryItem(type: RegistryAdminType) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  const client = clientMap[type];
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RegistryItemUpdateRequest }) =>
      client.update(token, id, data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["registry-admin", type] }),
  });
}

export function useDeleteRegistryItem(type: RegistryAdminType) {
  const token = useAccessToken();
  const queryClient = useQueryClient();
  const client = clientMap[type];
  return useMutation({
    mutationFn: (id: string) => client.delete(token, id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["registry-admin", type] }),
  });
}
