"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  contracts,
  type CentralContractCreateRequest,
  type CentralContractUpdateRequest,
  type ContractAuditLogParams,
  type ContractListParams,
  type CustomerContractOverrideCreateRequest,
  type CustomerContractOverrideUpdateRequest,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function useContractsList(params?: ContractListParams) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["contracts", params],
    queryFn: () => contracts.list(token, params),
    enabled: !!token,
  });
}

export function useContract(contractId: string) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["contracts", contractId],
    queryFn: () => contracts.get(token, contractId),
    enabled: !!token && !!contractId,
  });
}

export function useCreateContract() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CentralContractCreateRequest) =>
      contracts.create(token, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });
}

export function useUpdateContract(contractId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CentralContractUpdateRequest) =>
      contracts.update(token, contractId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });
}

export function useDeleteContract() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (contractId: string) => contracts.delete(token, contractId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });
}

export function useContractAuditLog(params?: ContractAuditLogParams) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["contracts", "audit-log", params],
    queryFn: () => contracts.getAuditLog(token, params),
    enabled: !!token,
  });
}

export function useProjectOverrides(projectId: string, params?: { offset?: number; limit?: number }) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["projects", projectId, "contract-overrides", params],
    queryFn: () => contracts.getProjectOverrides(token, projectId, params),
    enabled: !!token && !!projectId,
  });
}

export function useApplyContractToProject(projectId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CustomerContractOverrideCreateRequest) =>
      contracts.applyToProject(token, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "contract-overrides"] });
      queryClient.invalidateQueries({ queryKey: ["contracts", "audit-log"] });
    },
  });
}

export function useUpdateOverride(projectId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ overrideId, data }: { overrideId: string; data: CustomerContractOverrideUpdateRequest }) =>
      contracts.updateOverride(token, projectId, overrideId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "contract-overrides"] });
      queryClient.invalidateQueries({ queryKey: ["contracts", "audit-log"] });
    },
  });
}

export function useSyncContracts(projectId: string) {
  const token = useAccessToken();

  return useMutation({
    mutationFn: () => contracts.syncToAgent(token, projectId),
  });
}
