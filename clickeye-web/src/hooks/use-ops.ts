"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ops, type OpsTableRowsParams } from "@/lib/api-client";
import { useAccessToken } from "@/hooks/use-access-token";

const OPS_KEY = ["ops"] as const;

// ─── 조회 ─────────────────────────────────────────────────────────────

export function useOpsContainers() {
  const token = useAccessToken();
  return useQuery({
    queryKey: [...OPS_KEY, "containers"],
    queryFn: () => ops.listContainers(token),
    enabled: !!token,
    refetchInterval: 15_000,
  });
}

export function useOpsPorts() {
  const token = useAccessToken();
  return useQuery({
    queryKey: [...OPS_KEY, "ports"],
    queryFn: () => ops.listPorts(token),
    enabled: !!token,
    refetchInterval: 15_000,
  });
}

export function useOpsEnv() {
  const token = useAccessToken();
  return useQuery({
    queryKey: [...OPS_KEY, "env"],
    queryFn: () => ops.listEnv(token),
    enabled: !!token,
  });
}

export function useOpsTables() {
  const token = useAccessToken();
  return useQuery({
    queryKey: [...OPS_KEY, "tables"],
    queryFn: () => ops.listTables(token),
    enabled: !!token,
  });
}

export function useOpsTableSchema(table: string, enabled = true) {
  const token = useAccessToken();
  return useQuery({
    queryKey: [...OPS_KEY, "tables", table, "schema"],
    queryFn: () => ops.getTableSchema(token, table),
    enabled: enabled && !!token && !!table,
  });
}

export function useOpsTableRows(table: string, params?: OpsTableRowsParams) {
  const token = useAccessToken();
  return useQuery({
    queryKey: [...OPS_KEY, "tables", table, "rows", params ?? {}],
    queryFn: () => ops.listTableRows(token, table, params),
    enabled: !!token && !!table,
  });
}

// ─── 변이 (env) ───────────────────────────────────────────────────────

export function usePutOpsEnv() {
  const token = useAccessToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      ops.putEnv(token, key, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...OPS_KEY, "env"] }),
  });
}

export function useDeleteOpsEnv() {
  const token = useAccessToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => ops.deleteEnv(token, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...OPS_KEY, "env"] }),
  });
}

export function useRenderOpsEnv() {
  const token = useAccessToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (confirm: boolean) => ops.renderEnv(token, confirm),
    onSuccess: () => qc.invalidateQueries({ queryKey: [...OPS_KEY, "env"] }),
  });
}

// ─── 변이 (테이블 행 CRUD) ────────────────────────────────────────────

function invalidateTableRows(
  qc: ReturnType<typeof useQueryClient>,
  table: string,
) {
  qc.invalidateQueries({ queryKey: [...OPS_KEY, "tables", table, "rows"] });
  qc.invalidateQueries({ queryKey: [...OPS_KEY, "tables"] });
}

export function useCreateOpsRow(table: string) {
  const token = useAccessToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      ops.createTableRow(token, table, values),
    onSuccess: () => invalidateTableRows(qc, table),
  });
}

export function useUpdateOpsRow(table: string) {
  const token = useAccessToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ pk, values }: { pk: string; values: Record<string, unknown> }) =>
      ops.updateTableRow(token, table, pk, values),
    onSuccess: () => invalidateTableRows(qc, table),
  });
}

export function useDeleteOpsRow(table: string) {
  const token = useAccessToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (pk: string) => ops.deleteTableRow(token, table, pk),
    onSuccess: () => invalidateTableRows(qc, table),
  });
}
