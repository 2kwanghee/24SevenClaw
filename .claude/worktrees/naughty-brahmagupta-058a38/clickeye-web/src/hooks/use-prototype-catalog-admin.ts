"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import {
  type PrototypeCatalogEntry,
  type PrototypeCatalogEntryCreate,
  type PrototypeCatalogEntryUpdate,
  type PrototypeTag,
  type PrototypeTagCreate,
  type PrototypeTagUpdate,
  prototypeCatalogAdmin,
  prototypeTagsAdmin,
} from "@/lib/api-client";

// ─── Catalog Entries ──────────────────────────────────────────────────────────

export function useCatalogEntries(params?: {
  is_active?: boolean;
  primary_tag?: string;
  offset?: number;
  limit?: number;
}) {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  return useQuery({
    queryKey: ["prototype-catalog-admin", params],
    queryFn: () => prototypeCatalogAdmin.list(token, { limit: 200, ...params }),
    enabled: !!token,
  });
}

export function useCreateCatalogEntry() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PrototypeCatalogEntryCreate) =>
      prototypeCatalogAdmin.create(token, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prototype-catalog-admin"] }),
  });
}

export function useUpdateCatalogEntry() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PrototypeCatalogEntryUpdate }) =>
      prototypeCatalogAdmin.update(token, id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prototype-catalog-admin"] }),
  });
}

export function useDeleteCatalogEntry() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => prototypeCatalogAdmin.delete(token, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prototype-catalog-admin"] }),
  });
}

// ─── Tags ─────────────────────────────────────────────────────────────────────

export function usePrototypeTags(params?: { is_active?: boolean }) {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  return useQuery({
    queryKey: ["prototype-tags-admin", params],
    queryFn: () => prototypeTagsAdmin.list(token, params),
    enabled: !!token,
  });
}

export function useCreatePrototypeTag() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: PrototypeTagCreate) => prototypeTagsAdmin.create(token, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prototype-tags-admin"] }),
  });
}

export function useUpdatePrototypeTag() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PrototypeTagUpdate }) =>
      prototypeTagsAdmin.update(token, id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prototype-tags-admin"] }),
  });
}

export function useDeletePrototypeTag() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => prototypeTagsAdmin.delete(token, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prototype-tags-admin"] }),
  });
}

export type { PrototypeCatalogEntry, PrototypeTag };
