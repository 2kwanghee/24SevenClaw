"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Key,
  Loader2,
  Save,
  Trash2,
} from "lucide-react";

import {
  anthropicCredentials,
  apiClient,
  type AnthropicCredentialsResponse,
  type ProjectResponse,
  ApiClientError,
} from "@/lib/api-client";
import { PostKeyChangeGuide } from "@/components/credentials/post-key-change-guide";

export default function AnthropicSettingsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saved, setSaved] = useState<AnthropicCredentialsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [guideOpen, setGuideOpen] = useState(false);
  const [staleProjects, setStaleProjects] = useState<ProjectResponse[]>([]);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await anthropicCredentials.get(token);
      setSaved(data);
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

  const canSave = apiKey.trim().startsWith("sk-ant-") && apiKey.trim().length >= 20;

  const handleSave = async () => {
    if (!token || !canSave) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await anthropicCredentials.save(token, apiKey.trim());
      setSaved(data);
      setApiKey("");
      setSuccess("Anthropic API 키가 저장되었습니다.");
      // 키 변경 후 stale 프로젝트 조회 → 가이드 모달 표시
      try {
        const resp = await apiClient.projects.list(token, { limit: 100 });
        const stale = resp.items.filter((p) => p.anthropic_key_status === "stale");
        setStaleProjects(stale);
        setGuideOpen(true);
      } catch {
        // 프로젝트 조회 실패는 저장 자체의 실패가 아니므로 무시
      }
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
      await anthropicCredentials.delete(token);
      setSaved(null);
      setApiKey("");
      setSuccess("Anthropic API 키가 삭제되었습니다.");
    } catch (err) {
      setError(err instanceof ApiClientError ? err.detail : "삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-700" />
      </div>
    );
  }

  return (
    <>
    <PostKeyChangeGuide
      open={guideOpen}
      onClose={() => setGuideOpen(false)}
      channel="anthropic"
      staleProjects={staleProjects}
      token={token}
    />
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Anthropic API 키</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          위자드 라이브 프리뷰에서 우선 사용됩니다. 미등록 시 서버 공용 키로 폴백됩니다.
        </p>
      </div>

      {/* 저장된 키 요약 */}
      {saved && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <h2 className="text-sm font-semibold text-emerald-700">저장된 API 키</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-[var(--text-muted)]">API 키</p>
              <p className="font-mono text-[var(--text-secondary)] mt-0.5">{saved.api_key_masked}</p>
            </div>
            <div>
              <p className="text-[var(--text-muted)]">마지막 업데이트</p>
              <p className="text-[var(--text-secondary)] mt-0.5">
                {new Date(saved.updated_at).toLocaleDateString("ko-KR")}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 입력 폼 */}
      <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 space-y-5">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
          <Key className="h-4 w-4 text-[var(--text-muted)]" />
          {saved ? "API 키 교체" : "API 키 등록"}
        </h2>

        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1.5">
            Anthropic API 키 <span className="text-red-600">*</span>
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={saved ? `현재: ${saved.api_key_masked} — 교체하려면 새 키 입력` : "sk-ant-api03-..."}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-200"
          />
          <p className="mt-1 text-[11px] text-[var(--text-muted)]">
            <a
              href="https://console.anthropic.com/settings/keys"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sky-700 hover:text-sky-900 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              console.anthropic.com → API Keys
            </a>
            {" "}에서 발급 (sk-ant-... 형식)
          </p>
        </div>

        {/* 안내 박스 */}
        <div className="flex items-start gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2.5 text-xs text-zinc-600">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-zinc-500" />
          <p>
            키는 서버에 Fernet 암호화로 저장됩니다. 위자드에서 솔루션 청사진 분석 시 이 키가 우선 사용되며,
            서버 키보다 본인 계정의 크레딧이 우선 소진됩니다.
          </p>
        </div>

        {/* 에러 / 성공 */}
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
            type="button"
            onClick={handleSave}
            disabled={saving || !canSave}
            className="flex items-center gap-2 rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            {saved ? "교체" : "저장"}
          </button>

          {saved && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-medium text-red-700 transition-all hover:bg-red-100 disabled:opacity-50"
            >
              {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              삭제
            </button>
          )}
        </div>
      </div>
    </div>
    </>
  );
}
