"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { CheckCircle2, Key, Link2, Loader2, Save, Trash2, AlertCircle } from "lucide-react";

import {
  linearCredentials,
  type LinearCredentialsSave,
  type LinearCredentialsResponse,
  ApiClientError,
} from "@/lib/api-client";

export default function LinearSettingsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

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

  const handleSave = async () => {
    if (!token || !apiKey.trim() || !teamId.trim()) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: LinearCredentialsSave = {
        api_key: apiKey.trim(),
        team_id: teamId.trim(),
        webhook_secret: webhookSecret.trim() || null,
        tunnel_url: tunnelUrl.trim() || null,
      };
      const data = await linearCredentials.save(token, payload);
      setSaved(data);
      setApiKey("");
      setSuccess("Linear 자격증명이 저장되었습니다.");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.detail : "저장에 실패했습니다.");
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
      setSuccess("Linear 자격증명이 삭제되었습니다.");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.detail : "삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-violet-400" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-xl font-bold text-white">Linear 연동</h1>
        <p className="mt-1 text-sm text-slate-500">
          AI Team의 작업이 사용자 Linear에 자동으로 이슈로 등록됩니다.
        </p>
      </div>

      {/* 현재 저장 상태 */}
      {saved && (
        <div className="rounded-2xl border border-violet-500/20 bg-violet-500/5 p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="h-4 w-4 text-violet-400" />
            <h2 className="text-sm font-semibold text-violet-300">저장된 자격증명</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-slate-500">API 키</p>
              <p className="font-mono text-slate-300 mt-0.5">{saved.api_key_masked}</p>
            </div>
            <div>
              <p className="text-slate-500">팀 ID</p>
              <p className="font-mono text-slate-300 mt-0.5">{saved.team_id}</p>
            </div>
            <div>
              <p className="text-slate-500">Webhook 시크릿</p>
              <p className="text-slate-300 mt-0.5">{saved.webhook_secret_set ? "설정됨 ✓" : "미설정"}</p>
            </div>
            <div>
              <p className="text-slate-500">터널 URL</p>
              <p className="truncate text-slate-300 mt-0.5">{saved.tunnel_url ?? "미설정"}</p>
            </div>
          </div>
          {saved.linear_webhook_id && (
            <p className="mt-3 text-[11px] text-slate-600">
              Linear Webhook ID: {saved.linear_webhook_id}
            </p>
          )}
        </div>
      )}

      {/* 입력 폼 */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 space-y-5">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Key className="h-4 w-4 text-slate-400" />
          {saved ? "자격증명 업데이트" : "자격증명 등록"}
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">
              Linear API 키 <span className="text-red-400">*</span>
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={saved ? "새 API 키를 입력하면 교체됩니다" : "lin_api_xxxxxxxx..."}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30"
            />
            <p className="mt-1 text-[11px] text-slate-600">
              Linear → Settings → API → Personal API keys
            </p>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1.5">
              팀 ID <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30"
            />
            <p className="mt-1 text-[11px] text-slate-600">
              Linear → Settings → Workspace → Teams → 팀 ID 복사
            </p>
          </div>

          <div className="border-t border-white/5 pt-4">
            <h3 className="text-xs font-medium text-slate-400 mb-3 flex items-center gap-1.5">
              <Link2 className="h-3.5 w-3.5" />
              Webhook 설정 (실시간 트래킹용, 선택사항)
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">터널 URL</label>
                <input
                  type="url"
                  value={tunnelUrl}
                  onChange={(e) => setTunnelUrl(e.target.value)}
                  placeholder="https://xxxx.trycloudflare.com"
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30"
                />
                <p className="mt-1 text-[11px] text-slate-600">
                  ZIP의 setup-tunnel.sh를 실행하면 자동으로 발급됩니다
                </p>
              </div>

              <div>
                <label className="block text-xs text-slate-500 mb-1">Webhook 시크릿</label>
                <input
                  type="password"
                  value={webhookSecret}
                  onChange={(e) => setWebhookSecret(e.target.value)}
                  placeholder="Linear Webhook 서명 시크릿"
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30"
                />
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
            <AlertCircle className="h-3.5 w-3.5 text-red-400" />
            <p className="text-xs text-red-300">{error}</p>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <p className="text-xs text-emerald-300">{success}</p>
          </div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleSave}
            disabled={saving || !apiKey.trim() || !teamId.trim()}
            className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            저장
          </button>

          {saved && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-2 text-sm font-medium text-red-400 transition-all hover:bg-red-500/10 disabled:opacity-50"
            >
              {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              삭제
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
