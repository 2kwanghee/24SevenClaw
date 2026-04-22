"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
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
  type LinearCredentialsSave,
  type LinearCredentialsResponse,
  ApiClientError,
} from "@/lib/api-client";
import { cn } from "@/lib/utils";

/* ── 설정 방법 아코디언 ── */

interface GuideBlockProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function GuideBlock({ title, children, defaultOpen = false }: GuideBlockProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-xs font-medium text-slate-300">
          <Info className="h-3.5 w-3.5 text-violet-400" />
          {title}
        </span>
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
        )}
      </button>
      {open && (
        <div className="border-t border-white/5 px-4 py-4 text-xs text-slate-400 space-y-3">
          {children}
        </div>
      )}
    </div>
  );
}

function CodeLine({ children }: { children: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-black/20 px-3 py-2 font-mono text-[11px] text-slate-300">
      <Terminal className="h-3 w-3 shrink-0 text-slate-500" />
      {children}
    </div>
  );
}

/* ── 터널 URL 설정 가이드 ── */

function TunnelGuide() {
  return (
    <GuideBlock title="터널 URL은 어떻게 얻나요?">
      <p className="leading-relaxed">
        터널 URL은 로컬 webhook 서버를 인터넷에서 접근 가능하게 해주는 외부 주소입니다.
        ZIP에 포함된 스크립트로 자동 설치됩니다.
      </p>
      <ol className="space-y-2.5 list-none">
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/20 text-[10px] font-semibold text-violet-400">1</span>
          <div>
            <p className="font-medium text-slate-300 mb-1">ZIP 압축 해제 후 실행</p>
            <CodeLine>bash scripts/setup-tunnel.sh</CodeLine>
          </div>
        </li>
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/20 text-[10px] font-semibold text-violet-400">2</span>
          <div>
            <p className="font-medium text-slate-300 mb-1">출력된 URL 복사</p>
            <div className="rounded-lg border border-white/5 bg-black/20 px-3 py-2 font-mono text-[11px] text-emerald-400">
              {"https://abc-xyz-123.trycloudflare.com"}
            </div>
            <p className="mt-1 text-slate-500">이 URL을 아래 입력란에 붙여넣으세요.</p>
          </div>
        </li>
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/20 text-[10px] font-semibold text-violet-400">3</span>
          <div>
            <p className="font-medium text-slate-300 mb-1">webhook 서버 실행 (별도 터미널)</p>
            <CodeLine>bash scripts/start-webhook.sh</CodeLine>
          </div>
        </li>
      </ol>
      <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 mt-1">
        <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-400" />
        <p className="text-amber-300/80">
          터널 프로세스가 실행 중일 때만 URL이 유효합니다. 재시작하면 URL이 바뀔 수 있으니 그때마다 여기서 업데이트해 주세요.
        </p>
      </div>
      <a
        href="https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 transition-colors"
      >
        <ExternalLink className="h-3 w-3" />
        Cloudflare Tunnel 공식 문서
      </a>
    </GuideBlock>
  );
}

/* ── Webhook 시크릿 가이드 ── */

function WebhookSecretGuide() {
  return (
    <GuideBlock title="Webhook 시크릿은 무엇인가요?">
      <p className="leading-relaxed">
        Linear가 로컬 서버로 이벤트를 보낼 때 서명 검증에 사용하는 임의의 문자열입니다.
        설정하지 않아도 동작하지만, 보안을 위해 설정을 권장합니다.
      </p>
      <div className="space-y-2">
        <p className="font-medium text-slate-300">터미널에서 랜덤 시크릿 생성:</p>
        <CodeLine>{"openssl rand -hex 32"}</CodeLine>
        <p className="text-slate-500">출력된 값을 복사해서 아래 입력란과 ZIP의 <code className="text-slate-300">.env</code> 파일의 <code className="text-slate-300">WEBHOOK_SECRET</code>에 동일하게 입력하세요.</p>
      </div>
      <div className="flex items-start gap-2 rounded-lg border border-violet-500/20 bg-violet-500/5 px-3 py-2">
        <Shield className="h-3.5 w-3.5 shrink-0 mt-0.5 text-violet-400" />
        <p className="text-violet-300/80">
          터널 URL 등록 시 ClickEye가 Linear Webhook을 자동으로 등록합니다. 여기서 입력한 시크릿이 그 webhook에 적용됩니다.
        </p>
      </div>
    </GuideBlock>
  );
}

/* ── 메인 페이지 ── */

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
          ? "저장 완료. Linear Webhook이 자동으로 등록되었습니다."
          : "Linear 자격증명이 저장되었습니다.",
      );
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
          AI Team의 작업이 Linear에 자동으로 이슈로 등록되고, 상태 변경 시 로컬 Claude가 자동으로 실행됩니다.
        </p>
      </div>

      {/* 저장된 자격증명 요약 */}
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
              <p className="font-mono text-slate-300 mt-0.5 truncate">{saved.team_id}</p>
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
            <div className="mt-3 flex items-center gap-1.5">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <p className="text-[11px] text-emerald-400/80">Linear Webhook 등록됨</p>
            </div>
          )}
        </div>
      )}

      {/* 입력 폼 */}
      <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-6 space-y-6">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Key className="h-4 w-4 text-slate-400" />
          {saved ? "자격증명 업데이트" : "자격증명 등록"}
        </h2>

        {/* API 키 + 팀 ID */}
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">
              Linear API 키{" "}
              {saved ? (
                <span className="text-slate-600">(변경하지 않으면 비워두세요)</span>
              ) : (
                <span className="text-red-400">*</span>
              )}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                saved
                  ? `현재: ${saved.api_key_masked} — 변경하려면 새 키 입력`
                  : "lin_api_xxxxxxxx..."
              }
              className={cn(
                "w-full rounded-lg border bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:ring-1",
                saved && !apiKey
                  ? "border-white/5 focus:border-slate-500/50 focus:ring-slate-500/20"
                  : "border-white/10 focus:border-violet-500/50 focus:ring-violet-500/30",
              )}
            />
            <p className="mt-1 text-[11px] text-slate-600">
              Linear → Settings → API → Personal API keys에서 발급
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
              Linear → Settings → Workspace → Teams → 팀 이름 클릭 → ID 복사
            </p>
          </div>
        </div>

        {/* Webhook 설정 */}
        <div className="border-t border-white/5 pt-5 space-y-4">
          <h3 className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <Link2 className="h-3.5 w-3.5 text-violet-400" />
            Webhook 설정
            <span className="text-slate-600 font-normal">(실시간 Claude 트리거용)</span>
          </h3>

          <div>
            <label className="block text-xs text-slate-500 mb-1.5">터널 URL</label>
            <input
              type="url"
              value={tunnelUrl}
              onChange={(e) => setTunnelUrl(e.target.value)}
              placeholder="https://xxxx.trycloudflare.com"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30"
            />
            <p className="mt-1 text-[11px] text-slate-600">
              ZIP의 <code className="text-slate-400">setup-tunnel.sh</code> 실행 후 출력된 URL
            </p>
          </div>

          <TunnelGuide />

          <div>
            <label className="block text-xs text-slate-500 mb-1.5">Webhook 시크릿 (선택)</label>
            <input
              type="password"
              value={webhookSecret}
              onChange={(e) => setWebhookSecret(e.target.value)}
              placeholder={saved?.webhook_secret_set ? "설정됨 — 변경하려면 새 값 입력" : "openssl rand -hex 32 로 생성"}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30"
            />
          </div>

          <WebhookSecretGuide />
        </div>

        {/* 에러 / 성공 메시지 */}
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
            disabled={saving || !canSave}
            className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            {saved ? "업데이트" : "저장"}
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
