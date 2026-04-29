"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import {
  rbac,
  type AuditLogParams,
  type OrgMemberAddRequest,
  type RoleUpdateRequest,
} from "@/lib/api-client";

function useAccessToken() {
  const { data: session } = useSession();
  return session?.accessToken ?? "";
}

export function usePermissions() {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["rbac", "permissions"],
    queryFn: () => rbac.getPermissions(token),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAdminUsers() {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => rbac.listUsers(token),
    enabled: !!token,
  });
}

export function useUpdateUserRole() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: RoleUpdateRequest }) =>
      rbac.updateUserRole(token, userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit-log"] });
    },
  });
}

export function useOrgMembers(orgId: string) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["org", orgId, "members"],
    queryFn: () => rbac.getOrgMembers(token, orgId),
    enabled: !!token && !!orgId,
  });
}

export function useAddOrgMember(orgId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: OrgMemberAddRequest) =>
      rbac.addOrgMember(token, orgId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org", orgId, "members"] });
    },
  });
}

export function useRemoveOrgMember(orgId: string) {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      rbac.removeOrgMember(token, orgId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org", orgId, "members"] });
    },
  });
}

export function useAuditLog(params?: AuditLogParams) {
  const token = useAccessToken();

  return useQuery({
    queryKey: ["admin", "audit-log", params],
    queryFn: () => rbac.getAuditLog(token, params),
    enabled: !!token,
  });
}
