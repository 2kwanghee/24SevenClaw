"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import {
  CheckCircle2,
  Key,
  Link2,
  Loader2,
  Save,
  Trash2,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Terminal,
  Info,
  ExternalLink,
  Shield,
} from "lucide-react";

import {
  linearCredentials,
  apiClient,
  type LinearCredentialsSave,
  type LinearCredentialsResponse,
  type ProjectResponse,
  ApiClientError,
} from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { PostKeyChangeGuide } from "@/components/credentials/post-key-change-guide";

/* ── 설정 방법 아코디언 ── */

interface GuideBlockProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function GuideBlock({ title, children, defaultOpen = false }: GuideBlockProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)]">
          <Info className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
          {title}
        </span>
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 text-[var(--text-muted)]" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-[var(--text-muted)]" />
        )}
      </button>
      {open && (
        <div className="border-t border-[var(--border-subtle)] px-4 py-4 text-xs text-[var(--text-secondary)] space-y-3">
          {children}
        </div>
      )}
    </div>
  );
}

function CodeLine({ children }: { children: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3 py-2 font-mono text-[11px] text-[var(--text-secondary)]">
      <Terminal className="h-3 w-3 shrink-0 text-[var(--text-muted)]" />
      {children}
    </div>
  );
}

/* ── 터널 URL 설정 가이드 ── */

function TunnelGuide() {
  const t = useTranslations("settings.linear.guide");
  return (
    <GuideBlock title={t("tunnelTitle")}>
      <p className="leading-relaxed">{t("tunnelDesc")}</p>
      <ol className="space-y-2.5 list-none">
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--bg-base)] text-[10px] font-semibold text-[var(--text-secondary)]">1</span>
          <div>
            <p className="font-medium text-[var(--text-secondary)] mb-1">{t("tunnelStep1Title")}</p>
            <CodeLine>bash start.sh</CodeLine>
          </div>
        </li>
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--bg-base)] text-[10px] font-semibold text-[var(--text-secondary)]">2</span>
          <div>
            <p className="font-medium text-[var(--text-secondary)] mb-1">{t("tunnelStep2Title")}</p>
            <CodeLine>{"cat .run/tunnel.url"}</CodeLine>
            <p className="mt-1 text-[var(--text-muted)]">{t("tunnelStep2Paste")}</p>
          </div>
        </li>
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--bg-base)] text-[10px] font-semibold text-[var(--text-secondary)]">3</span>
          <div>
            <p className="font-medium text-[var(--text-secondary)] mb-1">{t("tunnelStep3Title")}</p>
            <CodeLine>bash start.sh</CodeLine>
            <p className="mt-1 text-[var(--text-muted)]">{t("tunnelStep3Note")}</p>
          </div>
        </li>
      </ol>
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 mt-1">
        <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-700" />
        <p className="text-amber-700">{t("tunnelWarning")}</p>
      </div>
      <a
        href="https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-sky-700 hover:text-sky-900 transition-colors"
      >
        <ExternalLink className="h-3 w-3" />
        {t("tunnelDocsLink")}
      </a>
    </GuideBlock>
  );
}

/* ── Webhook 시크릿 가이드 ── */

function WebhookSecretGuide() {
  const t = useTranslations("settings.linear.guide");
  return (
    <GuideBlock title={t("webhookTitle")}>
      <p className="leading-relaxed">{t("webhookDesc")}</p>
      <div className="space-y-2">
        <p className="font-medium text-[var(--text-secondary)]">{t("webhookGenerateTitle")}</p>
        <CodeLine>{"openssl rand -hex 32"}</CodeLine>
        <p className="text-[var(--text-muted)]">{t("webhookPasteDesc")}</p>
      </div>
      <div className="flex items-start gap-2 rounded-lg border border-[var(--accent-soft)] bg-[var(--accent-soft)] px-3 py-2">
        <Shield className="h-3.5 w-3.5 shrink-0 mt-0.5 text-[var(--accent)]" />
        <p className="text-[var(--accent)]">{t("webhookNote")}</p>
      </div>
    </GuideBlock>
  );
}

/* ── 메인 페이지 ── */

export default function LinearSettingsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const t = useTranslations("settings.linear");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saved, setSaved] = useState<LinearCredentialsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [apiKey, setApiKey] = useState("");
  const [teamId, setTeamId] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [tunnelUrl, setTunnelUrl] = useState("");
  const [guideOpen, setGuideOpen] = useState(false);
  const [staleProjects, setStaleProjects] = useState<ProjectResponse[]>([]);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await linearCredentials.get(token);
      setSaved(data);
      setTeamId(data.team_id);
      setTunnelUrl(data.tunnel_url ?? "");
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 404) {
        setSaved(null);
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  // 저장된 자격증명이 있으면 API 키는 선택, 없으면 필수
  const canSave = saved
    ? teamId.trim().length > 0
    : apiKey.trim().length >= 10 && teamId.trim().length > 0;

  const handleSave = async () => {
    if (!token || !canSave) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: LinearCredentialsSave = {
        api_key: apiKey.trim() || null,   // 빈 값이면 null → 기존 키 유지
        team_id: teamId.trim(),
        webhook_secret: webhookSecret.trim() || null,
        tunnel_url: tunnelUrl.trim() || null,
      };
      const data = await linearCredentials.save(token, payload);
      setSaved(data);
      setApiKey("");
      setSuccess(
        data.linear_webhook_id
          ? t("saveSuccess_webhook")
          : t("saveSuccess"),
      );
      // 키 변경 후 stale 프로젝트 조회 → 가이드 모달 표시 (API 키가 포함된 경우만)
      if (payload.api_key) {
        try {
          const resp = await apiClient.projects.list(token, { limit: 100 });
          const stale = resp.items.filter((p) => p.linear_key_status === "stale");
          setStaleProjects(stale);
          setGuideOpen(true);
        } catch {
          // 프로젝트 조회 실패는 저장 자체의 실패가 아니므로 무시
        }
      }
    } catch (err) {
      setError(err instanceof ApiClientError ? err.detail : t("saveFail"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!token) return;
    setDeleting(true);
    setError(null);
    try {
      await linearCredentials.delete(token);
      setSaved(null);
      setApiKey("");
      setTeamId("");
      setWebhookSecret("");
      setTunnelUrl("");
      setSuccess(t("deleteSuccess"));
    } catch (err) {
      setError(err instanceof ApiClientError ? err.detail : t("deleteFail"));
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-[var(--text-secondary)]" />
      </div>
    );
  }

  return (
    <>
    <PostKeyChangeGuide
      open={guideOpen}
      onClose={() => setGuideOpen(false)}
      channel="linear"
      staleProjects={staleProjects}
      token={token}
    />
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
      </div>

      {/* 저장된 자격증명 요약 */}
      {saved && (
        <div className="rounded-2xl border border-[var(--accent-soft)] bg-[var(--accent-soft)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="h-4 w-4 text-[var(--accent)]" />
            <h2 className="text-sm font-semibold text-[var(--accent)]">{t("savedTitle")}</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-[var(--text-muted)]">{t("apiKeyLabel_header")}</p>
              <p className="font-mono text-[var(--text-secondary)] mt-0.5">{saved.api_key_masked}</p>
            </div>
            <div>
              <p className="text-[var(--text-muted)]">{t("teamIdLabel_header")}</p>
              <p className="font-mono text-[var(--text-secondary)] mt-0.5 truncate">{saved.team_id}</p>
            </div>
            <div>
              <p className="text-[var(--text-muted)]">{t("webhookSecretLabel_header")}</p>
              <p className="text-[var(--text-secondary)] mt-0.5">{saved.webhook_secret_set ? `${t("webhookSet")} ✓` : t("webhookNotSet")}</p>
            </div>
            <div>
              <p className="text-[var(--text-muted)]">{t("tunnelUrlLabel_header")}</p>
              <p className="truncate text-[var(--text-secondary)] mt-0.5">{saved.tunnel_url ?? t("tunnelNotSet")}</p>
            </div>
          </div>
          {saved.linear_webhook_id && (
            <div className="mt-3 flex items-center gap-1.5">
              <CheckCircle2 className="h-3 w-3 text-emerald-600" />
              <p className="text-[11px] text-emerald-700">{t("webhookRegistered")}</p>
            </div>
          )}
        </div>
      )}

      {/* 입력 폼 */}
      <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 space-y-6">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
          <Key className="h-4 w-4 text-[var(--text-muted)]" />
          {saved ? t("formTitle_update") : t("formTitle_new")}
        </h2>

        {/* API 키 + 팀 ID */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">
              {t("apiKeyLabel")}{" "}
              {saved ? (
                <span className="text-[var(--text-muted)]">{t("apiKeyKeepEmpty")}</span>
              ) : (
                <span className="text-red-600">*</span>
              )}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                saved
                  ? `Current: ${saved.api_key_masked}`
                  : "lin_api_xxxxxxxx..."
              }
              className={cn(
                "w-full rounded-lg border bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:ring-1",
                saved && !apiKey
                  ? "border-[var(--border-subtle)] focus:border-[var(--accent)] focus:ring-[var(--accent)]"
                  : "border-[var(--border-subtle)] focus:border-[var(--accent)] focus:ring-[var(--accent)]",
              )}
            />
            <p className="mt-1 text-[11px] text-[var(--text-muted)]">
              {t("apiKeyHelp")}
            </p>
          </div>

          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">
              {t("teamIdLabel")} <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
            />
            <p className="mt-1 text-[11px] text-[var(--text-muted)]">
              {t("teamIdHelp")}
            </p>
          </div>
        </div>

        {/* Webhook 설정 */}
        <div className="border-t border-[var(--border-subtle)] pt-5 space-y-4">
          <h3 className="text-xs font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
            <Link2 className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
            {t("webhookSectionTitle")}
            <span className="text-[var(--text-muted)] font-normal">{t("webhookSectionNote")}</span>
          </h3>

          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">{t("tunnelUrlLabel")}</label>
            <input
              type="url"
              value={tunnelUrl}
              onChange={(e) => setTunnelUrl(e.target.value)}
              placeholder="https://xxxx.trycloudflare.com"
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
            />
            <p className="mt-1 text-[11px] text-[var(--text-muted)]">
              {t("tunnelUrlHelp")}
            </p>
          </div>

          <TunnelGuide />

          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1.5">{t("webhookSecretLabel")}</label>
            <input
              type="password"
              value={webhookSecret}
              onChange={(e) => setWebhookSecret(e.target.value)}
              placeholder={saved?.webhook_secret_set ? t("webhookPlaceholderSet") : t("webhookPlaceholderUnset")}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
            />
          </div>

          <WebhookSecretGuide />
        </div>

        {/* 에러 / 성공 메시지 */}
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2">
            <AlertCircle className="h-3.5 w-3.5 text-red-700" />
            <p className="text-xs text-red-700">{error}</p>
          </div>
        )}
        {success && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" />
            <p className="text-xs text-emerald-700">{success}</p>
          </div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleSave}
            disabled={saving || !canSave}
            className="flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            {saved ? t("updateBtn") : t("saveBtn")}
          </button>

          {saved && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition-all hover:bg-red-100 disabled:opacity-50"
            >
              {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              {t("deleteBtn")}
            </button>
          )}
        </div>
      </div>
    </div>
    </>
  );
}
