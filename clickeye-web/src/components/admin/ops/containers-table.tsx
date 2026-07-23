"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";

import { useOpsContainers, useOpsPorts } from "@/hooks/use-ops";
import type { OpsContainer, OpsPort } from "@/lib/api-client";

function stateTone(state: string): string {
  const s = state.toLowerCase();
  if (s === "running") return "bg-green-50 text-green-700 border-green-200";
  if (s === "restarting" || s === "paused")
    return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-red-50 text-red-700 border-red-200";
}

function healthTone(health: string | null): string {
  const h = (health ?? "").toLowerCase();
  if (h === "healthy") return "bg-green-50 text-green-700 border-green-200";
  if (h === "starting") return "bg-amber-50 text-amber-700 border-amber-200";
  if (h === "unhealthy") return "bg-red-50 text-red-700 border-red-200";
  return "bg-[var(--bg-hover)] text-[var(--text-muted)] border-[var(--border-subtle)]";
}

function Badge({ tone, children }: { tone: string; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${tone}`}
    >
      {children}
    </span>
  );
}

export function ContainersTable() {
  const t = useTranslations("ops.containers");
  const containers = useOpsContainers();
  const ports = useOpsPorts();

  return (
    <div className="space-y-8">
      {/* 컨테이너 */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            {t("containersTitle")}
          </h2>
          {containers.isFetching && (
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-[var(--text-muted)]" />
          )}
        </div>

        {containers.isLoading ? (
          <Loading />
        ) : containers.isError ? (
          <ErrorRow message={t("error")} />
        ) : (containers.data ?? []).length === 0 ? (
          <EmptyRow message={t("empty")} />
        ) : (
          <BentoCard className="block overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                  <Th>{t("col.name")}</Th>
                  <Th>{t("col.image")}</Th>
                  <Th>{t("col.state")}</Th>
                  <Th>{t("col.health")}</Th>
                  <Th>{t("col.ports")}</Th>
                  <Th>{t("col.created")}</Th>
                </tr>
              </thead>
              <tbody>
                {(containers.data ?? []).map((c: OpsContainer) => (
                  <tr
                    key={c.name}
                    className="border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-hover)]"
                  >
                    <td className="px-4 py-3 font-medium text-[var(--text-primary)]">
                      {c.name}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)]">
                      {c.image}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={stateTone(c.state)}>{c.state}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={healthTone(c.health)}>
                        {c.health ?? t("noHealth")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)]">
                      {c.ports || "-"}
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
                      {c.created}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 포트 */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            {t("portsTitle")}
          </h2>
          {ports.isFetching && (
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-[var(--text-muted)]" />
          )}
        </div>

        {ports.isLoading ? (
          <Loading />
        ) : ports.isError ? (
          <ErrorRow message={t("error")} />
        ) : (ports.data ?? []).length === 0 ? (
          <EmptyRow message={t("empty")} />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-[var(--border-subtle)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                  <Th>{t("col.service")}</Th>
                  <Th>{t("col.host")}</Th>
                  <Th>{t("col.port")}</Th>
                  <Th>{t("col.reachable")}</Th>
                  <Th>{t("col.latency")}</Th>
                </tr>
              </thead>
              <tbody>
                {(ports.data ?? []).map((p: OpsPort) => (
                  <tr
                    key={`${p.service}-${p.port}`}
                    className="border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-hover)]"
                  >
                    <td className="px-4 py-3 font-medium text-[var(--text-primary)]">
                      {p.service}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)]">
                      {p.host}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--text-secondary)]">
                      {p.port}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        tone={
                          p.reachable
                            ? "bg-green-50 text-green-700 border-green-200"
                            : "bg-red-50 text-red-700 border-red-200"
                        }
                      >
                        {p.reachable ? t("reachable") : t("unreachable")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
                      {p.latency_ms !== null ? `${p.latency_ms} ms` : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-2.5 text-left text-xs font-medium text-[var(--text-muted)]">
      {children}
    </th>
  );
}

function Loading() {
  return (
    <div className="flex justify-center py-8">
      <Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" />
    </div>
  );
}

function EmptyRow({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--border-subtle)] py-8 text-center text-sm text-[var(--text-muted)]">
      {message}
    </div>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 py-6 text-center text-sm text-red-700">
      {message}
    </div>
  );
}
