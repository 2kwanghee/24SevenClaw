"use client";

import { ChevronDown, ChevronUp, Clock, ExternalLink, KeyRound, Plus, Trash2, ShieldCheck, CheckCircle2, XCircle, Wifi } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSession } from "next-auth/react";

import { integrations } from "@/lib/api-client";
import { useCatalogHooks, useCatalogSkills } from "@/hooks/use-catalog";
import { collectEnvVars } from "@/lib/catalog-helpers";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { cn } from "@/lib/utils";
import { IntegrationValidationBadge } from "../integration-validation-badge";

/* ------------------------------------------------------------------
  Anthropic 기본 키 — DB에 없는 고정 필수 키
------------------------------------------------------------------ */

interface RequiredKeyConfig {
  key: string;
  label: string;
  description: string;
  guideUrl?: string;
  guideLabel?: string;
}

const ANTHROPIC_KEY_CONFIG: RequiredKeyConfig = {
  key: "ANTHROPIC_API_KEY",
  label: "Anthropic API 키",
  description: "Claude AI 모델 호출에 필요한 인증 키",
  guideUrl: "https://console.anthropic.com",
  guideLabel: "console.anthropic.com",
};

function getAlwaysRequired(authMethod: string): RequiredKeyConfig[] {
  return authMethod === "api_key" ? [ANTHROPIC_KEY_CONFIG] : [];
}

/* ------------------------------------------------------------------
  필수 키 행 컴포넌트
------------------------------------------------------------------ */

interface RequiredKeyRowProps {
  config: RequiredKeyConfig;
  value: string;
  onChange: (key: string, value: string) => void;
  isDeferred?: boolean;
  onDefer?: () => void;
}

function RequiredKeyRow({ config, value, onChange, isDeferred = false, onDefer }: RequiredKeyRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const isSet = value.trim().length > 0;

  const handleSave = () => {
    onChange(config.key, draft);
    setIsEditing(false);
  };

  return (
    <div
      className={cn(
        "rounded-xl border px-4 py-3 transition-colors",
        isSet
          ? "border-emerald-200 bg-emerald-50"
          : isDeferred
            ? "border-amber-500/20 bg-amber-500/5"
            : "border-red-500/20 bg-red-500/5",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          {isSet ? (
            <CheckCircle2
              className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
              aria-hidden="true"
            />
          ) : isDeferred ? (
            <Clock
              className="mt-0.5 h-4 w-4 shrink-0 text-amber-500"
              aria-hidden="true"
            />
          ) : (
            <XCircle
              className="mt-0.5 h-4 w-4 shrink-0 text-red-600"
              aria-hidden="true"
            />
          )}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <code className="font-mono text-xs font-semibold text-zinc-700">
                {config.key}
              </code>
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                  isSet
                    ? "bg-emerald-50 text-emerald-600"
                    : isDeferred
                      ? "bg-amber-500/15 text-amber-500"
                      : "bg-red-500/15 text-red-600",
                )}
              >
                {isSet ? "설정됨" : isDeferred ? "나중에 입력" : "필수"}
              </span>
            </div>
            <p className="mt-0.5 text-[11px] text-zinc-500">
              {config.description}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {config.guideUrl && (
            <a
              href={config.guideUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-sky-400 transition-colors hover:bg-sky-500/10 hover:text-sky-300"
              aria-label={`${config.label} 발급 가이드 열기`}
            >
              <ExternalLink className="h-3 w-3" aria-hidden="true" />
              발급 가이드
            </a>
          )}
          <button
            type="button"
            onClick={() => {
              setDraft(value);
              setIsEditing((v) => !v);
            }}
            className="rounded-md px-2 py-1 text-[11px] font-medium text-zinc-500 transition-colors hover:bg-zinc-50 hover:text-zinc-700"
          >
            {isEditing ? "취소" : isSet ? "수정" : "입력"}
          </button>
          {!isSet && !isEditing && !isDeferred && onDefer && (
            <button
              type="button"
              onClick={onDefer}
              className="rounded-md px-2 py-1 text-[11px] font-medium text-amber-500 transition-colors hover:bg-amber-500/10"
              aria-label={`${config.label} 나중에 입력`}
            >
              나중에
            </button>
          )}
        </div>
      </div>

      {isEditing && (
        <div className="mt-2.5 flex gap-2">
          <input
            type="password"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSave();
              if (e.key === "Escape") setIsEditing(false);
            }}
            placeholder={`${config.key} 값 입력`}
            autoFocus
            className="flex-1 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 font-mono text-xs text-zinc-950 placeholder-zinc-400 outline-none transition-all focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400/20"
            aria-label={`${config.label} 입력`}
          />
          <button
            type="button"
            onClick={handleSave}
            disabled={!draft.trim()}
            className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            저장
          </button>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------
  StepSolutionEnv 메인 컴포넌트
------------------------------------------------------------------ */

const DEBOUNCE_MS = 800;

export function StepSolutionEnv() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken ?? null;

  const envVars = useSolutionWizardStore((s) => s.data.env.envVars);
  const authMethod = useSolutionWizardStore((s) => s.data.env.authMethod ?? "api_key");
  const deferredEnvVars = useSolutionWizardStore((s) => s.data.env.deferredEnvVars ?? []);
  const selectedSkills = useSolutionWizardStore((s) => s.data.agents.selectedSkills);
  const selectedHooks = useSolutionWizardStore((s) => s.data.agents.selectedHooks ?? []);
  const setEnv = useSolutionWizardStore((s) => s.setEnv);
  const envValidation = useSolutionWizardStore((s) => s.envValidation);
  const setEnvValidation = useSolutionWizardStore((s) => s.setEnvValidation);

  const { data: skillsData } = useCatalogSkills();
  const { data: hooksData } = useCatalogHooks();

  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [expandedGuides, setExpandedGuides] = useState<Set<string>>(new Set());

  const toggleGuide = (skillId: string) => {
    setExpandedGuides((prev) => {
      const next = new Set(prev);
      if (next.has(skillId)) next.delete(skillId);
      else next.add(skillId);
      return next;
    });
  };

  // 선택된 스킬/훅에서 env_vars 그룹별 수집
  const envGroups = collectEnvVars(skillsData?.items, hooksData?.items, selectedSkills, selectedHooks);

  // 전체 필수 키 = authMethod별 Anthropic 키 + 동적 수집된 required vars
  const alwaysRequired = getAlwaysRequired(authMethod);
  const allRequiredKeys = [
    ...alwaysRequired,
    ...envGroups.flatMap((g) =>
      g.vars.filter((v) => v.required).map((v) => ({ key: v.name, label: v.name, description: v.description ?? "" }))
    ),
  ];
  // 미입력이면서 deferred도 아닌 키만 "누락"으로 간주
  const missingKeys = allRequiredKeys.filter(
    (c) => !envVars[c.key]?.trim() && !deferredEnvVars.includes(c.key),
  );
  const satisfiedCount = allRequiredKeys.filter(
    (c) => !!envVars[c.key]?.trim() || deferredEnvVars.includes(c.key),
  ).length;

  const handleRequiredKeyChange = (key: string, value: string) => {
    // 값을 입력하면 deferred 목록에서 자동 제거
    const newDeferred = value.trim()
      ? deferredEnvVars.filter((k) => k !== key)
      : deferredEnvVars;
    setEnv({ envVars: { ...envVars, [key]: value }, deferredEnvVars: newDeferred });
  };

  const handleDefer = (key: string) => {
    if (!deferredEnvVars.includes(key)) {
      setEnv({ deferredEnvVars: [...deferredEnvVars, key] });
    }
  };

  /* ----------------------------------------------------------------
    Linear/Notion 검증 — 두 키가 모두 입력되면 debounce 후 검증
  ---------------------------------------------------------------- */
  const linearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const notionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const triggerLinearValidation = useCallback(
    (apiKey: string, teamId: string) => {
      if (linearTimerRef.current) clearTimeout(linearTimerRef.current);
      if (!apiKey.trim() || !teamId.trim()) {
        setEnvValidation({ linearStatus: "idle", linearMessage: "" });
        return;
      }
      setEnvValidation({ linearStatus: "loading", linearMessage: "검증 중..." });
      linearTimerRef.current = setTimeout(async () => {
        if (!token) return;
        try {
          const res = await integrations.validateLinear(token, {
            api_key: apiKey,
            team_id: teamId,
          });
          setEnvValidation({
            linearStatus: res.valid ? "valid" : "invalid",
            linearMessage: res.message,
          });
        } catch {
          setEnvValidation({
            linearStatus: "invalid",
            linearMessage: "검증 요청 실패. 네트워크를 확인하세요.",
          });
        }
      }, DEBOUNCE_MS);
    },
    [token, setEnvValidation],
  );

  const triggerNotionValidation = useCallback(
    (apiKey: string, databaseId: string) => {
      if (notionTimerRef.current) clearTimeout(notionTimerRef.current);
      if (!apiKey.trim() || !databaseId.trim()) {
        setEnvValidation({ notionStatus: "idle", notionMessage: "" });
        return;
      }
      setEnvValidation({ notionStatus: "loading", notionMessage: "검증 중..." });
      notionTimerRef.current = setTimeout(async () => {
        if (!token) return;
        try {
          const res = await integrations.validateNotion(token, {
            api_key: apiKey,
            database_id: databaseId,
          });
          setEnvValidation({
            notionStatus: res.valid ? "valid" : "invalid",
            notionMessage: res.message,
          });
        } catch {
          setEnvValidation({
            notionStatus: "invalid",
            notionMessage: "검증 요청 실패. 네트워크를 확인하세요.",
          });
        }
      }, DEBOUNCE_MS);
    },
    [token, setEnvValidation],
  );

  // envVars 변경 시 linear/notion 쌍 재검증 트리거
  useEffect(() => {
    if (selectedSkills.includes("linear")) {
      triggerLinearValidation(
        envVars["LINEAR_API_KEY"] ?? "",
        envVars["LINEAR_TEAM_ID"] ?? "",
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [envVars["LINEAR_API_KEY"], envVars["LINEAR_TEAM_ID"]]);

  useEffect(() => {
    if (selectedSkills.includes("notion")) {
      triggerNotionValidation(
        envVars["NOTION_API_KEY"] ?? "",
        envVars["NOTION_DATABASE_ID"] ?? "",
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [envVars["NOTION_API_KEY"], envVars["NOTION_DATABASE_ID"]]);

  const handleAdd = () => {
    const key = newKey.trim().toUpperCase().replace(/\s/g, "_");
    if (!key) return;
    setEnv({ envVars: { ...envVars, [key]: newValue } });
    setNewKey("");
    setNewValue("");
  };

  const handleRemove = (key: string) => {
    const next = { ...envVars };
    delete next[key];
    setEnv({ envVars: next });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  const allTrackedKeys = new Set([
    ...alwaysRequired.map((c) => c.key),
    ...envGroups.flatMap((g) => g.vars.map((v) => v.name)),
  ]);
  const extraEnvVars = Object.entries(envVars).filter(([key]) => !allTrackedKeys.has(key));

  return (
    <div className="space-y-6">
      {/* Claude 인증 방식 선택 */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-zinc-700">Claude 인증 방식</h3>
        <div className="space-y-2">
          {/* api_key 옵션 */}
          <label
            className={cn(
              "flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition-colors",
              authMethod === "api_key"
                ? "border-violet-500/50 bg-violet-500/5"
                : "border-zinc-200 hover:border-zinc-300"
            )}
          >
            <input
              type="radio"
              name="authMethod"
              value="api_key"
              checked={authMethod === "api_key"}
              onChange={() => setEnv({ authMethod: "api_key" })}
              className="mt-0.5 accent-violet-500"
            />
            <div>
              <p className="text-sm font-medium text-zinc-700">API 키</p>
              <p className="text-[11px] text-zinc-500">Anthropic Console에서 발급한 sk-ant-... 키를 직접 입력합니다.</p>
            </div>
          </label>

          {/* oauth_browser 옵션 */}
          <label
            className={cn(
              "flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition-colors",
              authMethod === "oauth_browser"
                ? "border-violet-500/50 bg-violet-500/5"
                : "border-zinc-200 hover:border-zinc-300"
            )}
          >
            <input
              type="radio"
              name="authMethod"
              value="oauth_browser"
              checked={authMethod === "oauth_browser"}
              onChange={() => setEnv({ authMethod: "oauth_browser" })}
              className="mt-0.5 accent-violet-500"
            />
            <div>
              <p className="text-sm font-medium text-zinc-700">브라우저 OAuth (claude login)</p>
              <p className="text-[11px] text-zinc-500">
                Claude Pro/Max 구독자 전용.{" "}
                <code className="text-violet-400">bash start.sh</code> 실행 시{" "}
                <code className="text-violet-400">claude login</code>이 자동으로 진행됩니다.
              </p>
            </div>
          </label>
        </div>

        {/* oauth_browser 안내 카드 */}
        {authMethod === "oauth_browser" && (
          <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-xs text-zinc-400">
            <code className="text-sky-300">ANTHROPIC_API_KEY</code>는 .env에 포함되지 않습니다.
            <br />
            <code className="text-sky-300">bash start.sh</code>를 실행하면 브라우저 로그인이 자동으로 시작됩니다.
          </div>
        )}
      </div>

      {/* Anthropic 기본 키 (api_key 모드에서만 표시) */}
      {authMethod === "api_key" && (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-zinc-700">
          필수 API 키
          <span className="ml-1.5 text-[11px] font-normal text-zinc-500">
            ({satisfiedCount}/{allRequiredKeys.length} 설정됨)
          </span>
        </h3>
        {alwaysRequired.map((config) => (
          <RequiredKeyRow
            key={config.key}
            config={config}
            value={envVars[config.key] ?? ""}
            onChange={handleRequiredKeyChange}
            isDeferred={deferredEnvVars.includes(config.key)}
            onDefer={() => handleDefer(config.key)}
          />
        ))}
      </div>
      )}

      {/* 선택된 스킬별 API 키 그룹 */}
      {envGroups.map((group) => {
        const isExpanded = expandedGuides.has(group.skillId);
        const hasGuide = !!group.bodyMd;
        return (
          <div key={group.skillId} className="space-y-2 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <KeyRound className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                <span className="text-sm font-medium text-zinc-700">{group.skillLabel}</span>
                <span className="rounded-full bg-amber-400/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">
                  API 키 필요
                </span>
              </div>
              {hasGuide && (
                <button
                  type="button"
                  onClick={() => toggleGuide(group.skillId)}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-sky-400 hover:bg-sky-500/10"
                  aria-expanded={isExpanded}
                >
                  {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  설정 가이드
                </button>
              )}
            </div>

            {/* 접이식 body_md 가이드 */}
            {hasGuide && isExpanded && (
              <div className="rounded-lg border border-zinc-200 bg-black/20 px-4 py-3">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children }) => <h1 className="mb-2 text-sm font-semibold text-zinc-950">{children}</h1>,
                    h2: ({ children }) => <h2 className="mb-1.5 mt-3 text-xs font-semibold text-zinc-700">{children}</h2>,
                    h3: ({ children }) => <h3 className="mb-1 mt-2 text-xs font-medium text-zinc-700">{children}</h3>,
                    p: ({ children }) => <p className="mb-1.5 text-xs text-zinc-500">{children}</p>,
                    ol: ({ children }) => <ol className="mb-1.5 list-decimal pl-4 text-xs text-zinc-500 space-y-0.5">{children}</ol>,
                    ul: ({ children }) => <ul className="mb-1.5 list-disc pl-4 text-xs text-zinc-500 space-y-0.5">{children}</ul>,
                    li: ({ children }) => <li>{children}</li>,
                    code: ({ children }) => <code className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[11px] text-zinc-700">{children}</code>,
                    pre: ({ children }) => <pre className="mb-2 overflow-auto rounded-lg bg-black/40 px-3 py-2 font-mono text-[11px] text-zinc-700">{children}</pre>,
                    a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:text-sky-300">{children}</a>,
                    strong: ({ children }) => <strong className="font-semibold text-zinc-700">{children}</strong>,
                  }}
                >
                  {group.bodyMd!}
                </ReactMarkdown>
              </div>
            )}

            {/* env_var 입력 필드 */}
            <div className="space-y-2 pt-1">
              {group.vars.map((envVar) => (
                <RequiredKeyRow
                  key={envVar.name}
                  config={{ key: envVar.name, label: envVar.name, description: envVar.description ?? "" }}
                  value={envVars[envVar.name] ?? ""}
                  onChange={handleRequiredKeyChange}
                  isDeferred={deferredEnvVars.includes(envVar.name)}
                  onDefer={() => handleDefer(envVar.name)}
                />
              ))}
            </div>

            {/* Linear 검증 뱃지 */}
            {group.skillId === "linear" && (
              <IntegrationValidationBadge
                name="Linear"
                status={envValidation.linearStatus}
                message={envValidation.linearMessage}
              />
            )}

            {/* Notion 검증 뱃지 */}
            {group.skillId === "notion" && (
              <IntegrationValidationBadge
                name="Notion"
                status={envValidation.notionStatus}
                message={envValidation.notionMessage}
              />
            )}
          </div>
        );
      })}

      {missingKeys.length > 0 && (
        <p
          role="alert"
          className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-400"
        >
          필수 키 {missingKeys.length}개가 미설정 상태입니다. 값을 입력하거나 &ldquo;나중에&rdquo; 버튼으로 나중에 입력하도록 지정하세요.
        </p>
      )}
      {deferredEnvVars.length > 0 && (
        <p
          role="status"
          className="rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2.5 text-xs text-zinc-500"
        >
          <Clock className="mr-1.5 inline h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
          나중에 입력할 키 {deferredEnvVars.length}개 — 최종 확인 단계에서 추가 입력할 수 있습니다.
        </p>
      )}

      {/* Webhook 터널 설정 (linear 선택 시) */}
      {selectedSkills.includes("linear") && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Wifi className="h-4 w-4 text-violet-400" aria-hidden="true" />
            <h3 className="text-sm font-medium text-zinc-700">
              실시간 트래킹 방식
              <span className="ml-1.5 text-[11px] font-normal text-zinc-500">(선택)</span>
            </h3>
          </div>
          <p className="text-xs text-zinc-500">
            Linear 이슈 상태 변경 시 로컬 Claude를 자동으로 실행하는 방식을 선택하세요.
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {(["cloudflare", "ngrok", "polling"] as const).map((provider) => {
              const current = envVars["TUNNEL_PROVIDER"] ?? "cloudflare";
              const labels: Record<string, { title: string; desc: string }> = {
                cloudflare: { title: "Cloudflare Tunnel", desc: "무료 · 정적 URL (권장)" },
                ngrok: { title: "ngrok", desc: "유료 고정 / 무료 임시 URL" },
                polling: { title: "30초 폴링", desc: "webhook 불필요 · 지연 30초" },
              };
              const isSelected = current === provider;
              return (
                <button
                  key={provider}
                  type="button"
                  onClick={() =>
                    setEnv({
                      envVars: { ...envVars, TUNNEL_PROVIDER: provider },
                    })
                  }
                  className={cn(
                    "rounded-xl border px-3 py-2.5 text-left transition-colors",
                    isSelected
                      ? "border-violet-500/40 bg-violet-500/10"
                      : "border-zinc-200 bg-zinc-50 hover:border-zinc-300",
                  )}
                >
                  <p className={cn("text-xs font-medium", isSelected ? "text-violet-300" : "text-zinc-700")}>
                    {labels[provider].title}
                  </p>
                  <p className="mt-0.5 text-[11px] text-zinc-500">{labels[provider].desc}</p>
                </button>
              );
            })}
          </div>

          {(envVars["TUNNEL_PROVIDER"] ?? "cloudflare") === "ngrok" && (
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2.5">
              <label className="block text-xs text-zinc-500 mb-1.5">
                ngrok 인증 토큰{" "}
                <a
                  href="https://dashboard.ngrok.com/get-started/your-authtoken"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sky-400 hover:text-sky-300"
                >
                  (ngrok.com에서 발급)
                </a>
              </label>
              <input
                type="password"
                value={envVars["NGROK_AUTH_TOKEN"] ?? ""}
                onChange={(e) =>
                  setEnv({ envVars: { ...envVars, NGROK_AUTH_TOKEN: e.target.value } })
                }
                placeholder="ngrok 인증 토큰"
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 font-mono text-xs text-zinc-950 placeholder-zinc-400 outline-none focus:border-violet-500/50"
              />
            </div>
          )}

          {(envVars["TUNNEL_PROVIDER"] ?? "cloudflare") === "cloudflare" && (
            <p className="text-[11px] text-zinc-500">
              ZIP 압축 해제 후 <code className="text-zinc-500">bash scripts/setup-tunnel.sh</code>을 실행하면 cloudflared가 자동 설치됩니다.
            </p>
          )}
          {(envVars["TUNNEL_PROVIDER"] ?? "cloudflare") === "polling" && (
            <p className="text-[11px] text-zinc-500">
              <code className="text-zinc-500">python3 scripts/linear_watcher.py</code>를 실행하면 30초마다 Linear를 폴링합니다. webhook 서버 불필요.
            </p>
          )}
        </div>
      )}

      {/* 보안 안내 */}
      <div className="flex items-start gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
        <ShieldCheck
          className="mt-0.5 h-4 w-4 shrink-0 text-yellow-400"
          aria-hidden="true"
        />
        <p className="text-xs text-zinc-500">
          {authMethod === "api_key" ? (
            <>
              입력한 키는 ZIP 파일의{" "}
              <code className="text-yellow-300">.env</code>에 저장됩니다.
              ZIP 파일은 공유하지 마세요. 방법을 모르는 경우 ZIP의{" "}
              <code className="text-yellow-300">docs/api-keys/</code> 폴더를 참고하세요.
            </>
          ) : (
            <>
              브라우저 OAuth 모드에서는 Anthropic 키가 .env에 포함되지 않습니다.
              <code className="ml-1 text-yellow-300">bash start.sh</code> 실행 시 claude login이 자동으로 진행됩니다.
            </>
          )}
        </p>
      </div>

      {/* 추가 환경변수 목록 */}
      {extraEnvVars.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-zinc-700">
            추가 환경변수
          </h3>
          {extraEnvVars.map(([key, value]) => (
            <div
              key={key}
              className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2"
            >
              <KeyRound
                className="h-3.5 w-3.5 shrink-0 text-emerald-600"
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 font-mono text-xs text-zinc-700">
                {key}
              </span>
              <span className="min-w-0 flex-1 truncate font-mono text-xs text-zinc-500">
                {value ? "••••••••" : "(비어있음)"}
              </span>
              <button
                type="button"
                onClick={() => handleRemove(key)}
                aria-label={`${key} 제거`}
                className="rounded-md p-1 text-zinc-500 transition-colors hover:bg-red-500/10 hover:text-red-600"
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 환경변수 추가 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-zinc-700">
          환경변수 추가{" "}
          <span className="text-xs font-normal text-zinc-500">(선택)</span>
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="KEY_NAME"
            className="w-1/3 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2.5 font-mono text-sm text-zinc-950 placeholder-zinc-400 outline-none transition-all focus:border-zinc-400 focus:ring-2 focus:ring-zinc-400/20"
          />
          <input
            type="text"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="값 (나중에 입력 가능)"
            className="flex-1 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2.5 text-sm text-zinc-950 placeholder-zinc-400 outline-none transition-all focus:border-zinc-400 focus:ring-2 focus:ring-zinc-400/20"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!newKey.trim()}
            className="flex items-center gap-1.5 rounded-xl bg-zinc-900 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
