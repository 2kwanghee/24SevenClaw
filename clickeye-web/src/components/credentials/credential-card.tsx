"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
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
  ApiClientError,
  type AnthropicCredentialsResponse,
} from "@/lib/api-client";

interface CredentialCardProps {
  credentialType: "api_key";
  title: string;
  description: string;
  placeholder: string;
  validate: (value: string) => string | null;
  externalLink?: { href: string; label: string };
  totalDays?: number;
  helperText?: ReactNode;
  onChanged?: () => void;
}

function ExpiryBadge({ updatedAt, totalDays }: { updatedAt: string; totalDays: number }) {
  const elapsed = Math.floor((Date.now() - new Date(updatedAt).getTime()) / 86400000);
  const daysLeft = Math.max(0, totalDays - elapsed);

  const colorClass =
    daysLeft <= 30
      ? "text-red-700 bg-red-100"
      : daysLeft <= 60
        ? "text-amber-700 bg-amber-100"
        : "text-zinc-500 bg-zinc-100";

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${colorClass}`}>
      만료까지 {daysLeft}일
    </span>
  );
}

export function CredentialCard({
  credentialType,
  title,
  description,
  placeholder,
  validate,
  externalLink,
  totalDays,
  helperText,
  onChanged,
}: CredentialCardProps) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saved, setSaved] = useState<AnthropicCredentialsResponse | null>(null);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await anthropicCredentials.get(token);
      setSaved(data);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 404) setSaved(null);
    } finally {
      setLoading(false);
    }
  }, [token, credentialType]);

  useEffect(() => {
    void load();
  }, [load]);

  const validationError = value.trim() ? validate(value.trim()) : null;
  const canSave = !!value.trim() && !validationError;

  const handleSave = async () => {
    if (!token || !canSave) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await anthropicCredentials.save(token, value.trim());
      setSaved(data);
      setValue("");
      setSuccess(`${title}이(가) 저장되었습니다.`);
      onChanged?.();
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
      setValue("");
      setSuccess(`${title}이(가) 삭제되었습니다.`);
      onChanged?.();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.detail : "삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-10">
        <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {saved && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <h3 className="text-sm font-semibold text-emerald-700">저장된 {title}</h3>
            {totalDays !== undefined && (
              <ExpiryBadge updatedAt={saved.updated_at} totalDays={totalDays} />
            )}
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-[var(--text-muted)]">저장됨</p>
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

      <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 space-y-5">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
          <Key className="h-4 w-4 text-[var(--text-muted)]" />
          {saved ? `${title} 교체` : `${title} 등록`}
        </h3>

        <p className="text-xs text-[var(--text-muted)]">{description}</p>

        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1.5">
            {title} <span className="text-red-600">*</span>
          </label>
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={saved ? `현재: ${saved.api_key_masked} — 교체하려면 입력` : placeholder}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-200"
          />
          {value.trim() && validationError && (
            <p className="mt-1 text-[11px] text-red-600">{validationError}</p>
          )}
          {externalLink && (
            <p className="mt-1 text-[11px] text-[var(--text-muted)]">
              <a
                href={externalLink.href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sky-700 hover:text-sky-900 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                {externalLink.label}
              </a>
            </p>
          )}
        </div>

        {helperText && (
          <div className="flex items-start gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2.5 text-xs text-zinc-600">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-zinc-500" />
            <p>{helperText}</p>
          </div>
        )}

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
            className="flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-all hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
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
  );
}
