"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { z } from "zod";
import {
  CheckCircle2,
  Key,
  Link2,
  Loader2,
  Save,
  Trash2,
  AlertCircle,
  Info,
} from "lucide-react";

import { BentoCard } from "@/components/ui/bento";
import {
  projectLinearCredentials,
  ApiClientError,
  type ProjectLinearCredentialsResponse,
} from "@/lib/api-client";

interface ProjectLinearCardProps {
  projectId: string;
}

export function ProjectLinearCard({ projectId }: ProjectLinearCardProps) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const t = useTranslations("projectLinear");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saved, setSaved] = useState<ProjectLinearCredentialsResponse | null>(null);

  const schema = useMemo(
    () =>
      z.object({
        api_key: z.string().min(10, t("apiKeyInvalid")),
        team_id: z.string().min(1, t("teamIdRequired")),
        webhook_secret: z.string().optional(),
        tunnel_url: z.string().optional(),
      }),
    [t],
  );
  type FormData = z.infer<typeof schema>;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { api_key: "", team_id: "", webhook_secret: "", tunnel_url: "" },
  });

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await projectLinearCredentials.get(token, projectId);
      setSaved(data);
      setValue("team_id", data.team_id);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 404) {
        setSaved(null);
      }
    } finally {
      setLoading(false);
    }
  }, [token, projectId, setValue]);

  useEffect(() => {
    void load();
  }, [load]);

  const onSubmit = async (form: FormData) => {
    if (!token) return;
    setSaving(true);
    try {
      const data = await projectLinearCredentials.save(token, projectId, {
        api_key: form.api_key.trim(),
        team_id: form.team_id.trim(),
        webhook_secret: form.webhook_secret?.trim() || null,
        tunnel_url: form.tunnel_url?.trim() || null,
      });
      setSaved(data);
      reset({ api_key: "", team_id: data.team_id, webhook_secret: "", tunnel_url: "" });
      toast.success(t("saveSuccess"));
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.detail : t("saveFail"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!token) return;
    setDeleting(true);
    try {
      await projectLinearCredentials.delete(token, projectId);
      setSaved(null);
      reset({ api_key: "", team_id: "", webhook_secret: "", tunnel_url: "" });
      toast.success(t("deleteSuccess"));
    } catch (err) {
      toast.error(err instanceof ApiClientError ? err.detail : t("deleteFail"));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <BentoCard className="space-y-6">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-semibold text-[var(--text-primary)]">
          <Key className="h-4 w-4 text-[var(--text-muted)]" />
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
      </div>

      {/* 안내: 프로젝트 키가 보드 티켓 상세 동작에 사용됨 */}
      <div className="flex items-start gap-2 rounded-lg border border-[var(--accent-soft)] bg-[var(--accent-soft)] px-3 py-2">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--accent)]" />
        <p className="text-xs text-[var(--accent)]">{t("boardNotice")}</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-[var(--text-secondary)]" />
        </div>
      ) : (
        <>
          {/* 현재 상태 */}
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-3">
            {saved ? (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-[var(--text-muted)]">{t("statusLabel")}</p>
                  <p className="mt-0.5 flex items-center gap-1.5 font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {t("registered")}
                  </p>
                </div>
                <div>
                  <p className="text-[var(--text-muted)]">{t("apiKeyMaskedLabel")}</p>
                  <p className="mt-0.5 font-mono text-[var(--text-secondary)]">
                    {saved.api_key_masked}
                  </p>
                </div>
                <div className="col-span-2">
                  <p className="text-[var(--text-muted)]">{t("teamIdLabel")}</p>
                  <p className="mt-0.5 truncate font-mono text-[var(--text-secondary)]">
                    {saved.team_id}
                  </p>
                </div>
                {saved.linear_webhook_id ? (
                  <div className="col-span-2 flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                    <Link2 className="h-3.5 w-3.5" />
                    <span className="font-medium">{t("webhookRegistered")}</span>
                  </div>
                ) : saved.webhook_secret_set ? (
                  <div className="col-span-2 flex items-center gap-1.5 text-[var(--text-secondary)]">
                    <AlertCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                    <span>{t("webhookSecretOnly")}</span>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
                <AlertCircle className="h-3.5 w-3.5" />
                {t("notRegistered")}
              </p>
            )}
          </div>

          {/* 입력 폼 */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
                {t("apiKeyLabel")} <span className="text-red-600">*</span>
              </label>
              <input
                type="password"
                autoComplete="off"
                placeholder={saved ? t("apiKeyPlaceholderUpdate") : "lin_api_xxxxxxxx..."}
                {...register("api_key")}
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
              />
              {errors.api_key && (
                <p className="mt-1 text-[11px] text-red-600">{errors.api_key.message}</p>
              )}
              <p className="mt-1 text-[11px] text-[var(--text-muted)]">{t("apiKeyHelp")}</p>
            </div>

            <div>
              <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
                {t("teamIdLabel")} <span className="text-red-600">*</span>
              </label>
              <input
                type="text"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                {...register("team_id")}
                className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
              />
              {errors.team_id && (
                <p className="mt-1 text-[11px] text-red-600">{errors.team_id.message}</p>
              )}
              <p className="mt-1 text-[11px] text-[var(--text-muted)]">{t("teamIdHelp")}</p>
            </div>

            {/* Webhook 설정 (옵션) */}
            <div className="space-y-4 border-t border-[var(--border-subtle)] pt-4">
              <h3 className="flex items-center gap-1.5 text-xs font-medium text-[var(--text-secondary)]">
                <Link2 className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
                {t("webhookSectionTitle")}
                <span className="font-normal text-[var(--text-muted)]">
                  {t("optional")}
                </span>
              </h3>

              <div>
                <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
                  {t("webhookSecretLabel")}
                </label>
                <input
                  type="password"
                  autoComplete="off"
                  placeholder="lin_wh_... (선택)"
                  {...register("webhook_secret")}
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
                />
                <p className="mt-1 text-[11px] text-[var(--text-muted)]">{t("webhookSecretHelp")}</p>
              </div>

              <div>
                <label className="mb-1.5 block text-xs text-[var(--text-muted)]">
                  {t("tunnelUrlLabel")}
                </label>
                <input
                  type="text"
                  placeholder="https://xxxx.trycloudflare.com"
                  {...register("tunnel_url")}
                  className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
                />
                <p className="mt-1 text-[11px] text-[var(--text-muted)]">{t("tunnelUrlHelp")}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5" />
                )}
                {saved ? t("updateBtn") : t("saveBtn")}
              </button>

              {saved && (
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition-all hover:bg-red-100 disabled:opacity-50 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300 dark:hover:bg-red-950/60"
                >
                  {deleting ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="h-3.5 w-3.5" />
                  )}
                  {t("deleteBtn")}
                </button>
              )}
            </div>
          </form>
        </>
      )}
    </BentoCard>
  );
}
