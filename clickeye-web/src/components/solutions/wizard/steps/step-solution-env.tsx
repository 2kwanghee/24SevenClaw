"use client";

import { ChevronDown, ChevronUp, Clock, ExternalLink, KeyRound, Plus, Trash2, ShieldCheck, CheckCircle2, XCircle, Wifi } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useSession } from "next-auth/react";

import { integrations } from "@/lib/api-client";
import { useCatalogHooks, useCatalogSkills } from "@/hooks/use-catalog";
import { collectEnvVars } from "@/lib/catalog-helpers";
import {
  checkLinearInputs,
  checkNotionInputs,
  describeIntegrationError,
  sanitizeIntegrationInput,
} from "@/lib/integration-validators";
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
  // label/description 은 렌더 시 i18n(anthropicKeyLabel/anthropicKeyDesc)으로 덮어쓴다.
  label: "Anthropic API key",
  description: "Authentication key required to call Claude AI models",
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

export function RequiredKeyRow({ config, value, onChange, isDeferred = false, onDefer }: RequiredKeyRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [sanitizedDropped, setSanitizedDropped] = useState(false);
  const isSet = value.trim().length > 0;
  const tEnv = useTranslations("wizard.step6.env");

  const handleSave = () => {
    onChange(config.key, draft);
    setIsEditing(false);
    setSanitizedDropped(false);
  };

  const handleDraftChange = (raw: string) => {
    const sanitized = sanitizeIntegrationInput(raw);
    setDraft(sanitized);
    setSanitizedDropped(sanitized.length !== raw.length);
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
                {isSet ? tEnv("statusSet") : isDeferred ? tEnv("statusDeferred") : tEnv("statusRequired")}
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
              aria-label={`${config.label} ${tEnv("guideLink")}`}
            >
              <ExternalLink className="h-3 w-3" aria-hidden="true" />
              {tEnv("guideLink")}
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
            {isEditing ? tEnv("cancelBtn") : isSet ? tEnv("editBtn") : tEnv("enterBtn")}
          </button>
          {!isSet && !isEditing && !isDeferred && onDefer && (
            <button
              type="button"
              onClick={onDefer}
              className="rounded-md px-2 py-1 text-[11px] font-medium text-amber-500 transition-colors hover:bg-amber-500/10"
              aria-label={`${config.label} ${tEnv("laterBtn")}`}
            >
              {tEnv("laterBtn")}
            </button>
          )}
        </div>
      </div>

      {isEditing && (
        <>
          <div className="mt-2.5 flex gap-2">
            <input
              type="password"
              value={draft}
              onChange={(e) => handleDraftChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") setIsEditing(false);
              }}
              placeholder={`${config.key}`}
              autoFocus
              aria-invalid={sanitizedDropped}
              className={`flex-1 rounded-lg border bg-zinc-50 px-3 py-1.5 font-mono text-xs text-zinc-950 placeholder-zinc-400 outline-none transition-all focus:ring-1 ${
                sanitizedDropped
                  ? "border-amber-400 focus:border-amber-500 focus:ring-amber-200"
                  : "border-zinc-200 focus:border-zinc-400 focus:ring-zinc-400/20"
              }`}
              aria-label={`${config.label} ${tEnv("enterBtn")}`}
            />
            <button
              type="button"
              onClick={handleSave}
              disabled={!draft.trim()}
              className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {tEnv("saveBtn")}
            </button>
          </div>
          {sanitizedDropped && (
            <p className="mt-1 text-[10px] text-amber-600">
              {tEnv("nonAsciiWarning")}
            </p>
          )}
        </>
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
  const t = useTranslations("wizard.step6.env");

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
  // Anthropic 고정 키의 label/description 은 i18n 으로 덮어쓴다 (DB 동적 키는 그대로).
  const alwaysRequired = getAlwaysRequired(authMethod).map((c) =>
    c.key === "ANTHROPIC_API_KEY"
      ? { ...c, label: t("anthropicKeyLabel"), description: t("anthropicKeyDesc") }
      : c,
  );
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
      // 클라이언트 사전 검증: 비-ASCII 입력은 fetch 호출 자체가 실패할 수 있어 차단
      const check = checkLinearInputs(apiKey, teamId);
      if (!check.ok) {
        setEnvValidation({ linearStatus: "invalid", linearMessage: check.message });
        return;
      }
      setEnvValidation({ linearStatus: "loading", linearMessage: t("validating") });
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
        } catch (err) {
          setEnvValidation({
            linearStatus: "invalid",
            linearMessage: describeIntegrationError(err),
          });
        }
      }, DEBOUNCE_MS);
    },
    [token, setEnvValidation, t],
  );

  const triggerNotionValidation = useCallback(
    (apiKey: string, databaseId: string) => {
      if (notionTimerRef.current) clearTimeout(notionTimerRef.current);
      if (!apiKey.trim() || !databaseId.trim()) {
        setEnvValidation({ notionStatus: "idle", notionMessage: "" });
        return;
      }
      const check = checkNotionInputs(apiKey, databaseId);
      if (!check.ok) {
        setEnvValidation({ notionStatus: "invalid", notionMessage: check.message });
        return;
      }
      setEnvValidation({ notionStatus: "loading", notionMessage: t("validating") });
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
        } catch (err) {
          setEnvValidation({
            notionStatus: "invalid",
            notionMessage: describeIntegrationError(err),
          });
        }
      }, DEBOUNCE_MS);
    },
    [token, setEnvValidation, t],
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
        <h3 className="text-sm font-medium text-zinc-700">{t("authTitle")}</h3>
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
              <p className="text-sm font-medium text-zinc-700">{t("authApiKeyLabel")}</p>
              <p className="text-[11px] text-zinc-500">{t("authApiKeyDesc")}</p>
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
              <p className="text-sm font-medium text-zinc-700">{t("authOAuthLabel")}</p>
              <p className="text-[11px] text-zinc-500">{t("authOAuthDesc")}</p>
            </div>
          </label>
        </div>

        {/* oauth_browser 안내 카드 */}
        {authMethod === "oauth_browser" && (
          <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-xs text-zinc-400">
            {t("oauthNote")}
          </div>
        )}
      </div>

      {/* Anthropic 기본 키 (api_key 모드에서만 표시) */}
      {authMethod === "api_key" && (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-zinc-700">
          {t("requiredKeysTitle")}
          <span className="ml-1.5 text-[11px] font-normal text-zinc-500">
            {t("requiredKeysSummary", { satisfied: satisfiedCount, total: allRequiredKeys.length })}
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
                  {t("apiKeyNeeded")}
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
                  {t("setupGuideBtn")}
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
          {t("missingKeysAlert", { count: missingKeys.length })}
        </p>
      )}
      {deferredEnvVars.length > 0 && (
        <p
          role="status"
          className="rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2.5 text-xs text-zinc-500"
        >
          <Clock className="mr-1.5 inline h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
          {t("deferredKeysNote", { count: deferredEnvVars.length })}
        </p>
      )}

      {/* Webhook 터널 설정 (linear 선택 시) */}
      {selectedSkills.includes("linear") && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Wifi className="h-4 w-4 text-violet-400" aria-hidden="true" />
            <h3 className="text-sm font-medium text-zinc-700">
              {t("trackingTitle")}
              <span className="ml-1.5 text-[11px] font-normal text-zinc-500">{t("trackingOptional")}</span>
            </h3>
          </div>
          <p className="text-xs text-zinc-500">
            {t("trackingDesc")}
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {(["cloudflare", "ngrok", "polling"] as const).map((provider) => {
              const current = envVars["TUNNEL_PROVIDER"] ?? "cloudflare";
              const providerLabels: Record<string, { title: string; desc: string }> = {
                cloudflare: { title: t("cfTitle"), desc: t("cfDesc") },
                ngrok: { title: t("ngrokTitle"), desc: t("ngrokDesc") },
                polling: { title: t("pollingTitle"), desc: t("pollingDesc") },
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
                    {providerLabels[provider].title}
                  </p>
                  <p className="mt-0.5 text-[11px] text-zinc-500">{providerLabels[provider].desc}</p>
                </button>
              );
            })}
          </div>

          {(envVars["TUNNEL_PROVIDER"] ?? "cloudflare") === "ngrok" && (
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2.5">
              <label className="block text-xs text-zinc-500 mb-1.5">
                {t("ngrokToken")}{" "}
                <a
                  href="https://dashboard.ngrok.com/get-started/your-authtoken"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sky-400 hover:text-sky-300"
                >
                  {t("ngrokTokenLink")}
                </a>
              </label>
              <input
                type="password"
                value={envVars["NGROK_AUTH_TOKEN"] ?? ""}
                onChange={(e) =>
                  setEnv({
                    envVars: {
                      ...envVars,
                      NGROK_AUTH_TOKEN: sanitizeIntegrationInput(e.target.value),
                    },
                  })
                }
                placeholder={t("ngrokToken")}
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-1.5 font-mono text-xs text-zinc-950 placeholder-zinc-400 outline-none focus:border-violet-500/50"
              />
            </div>
          )}

          {(envVars["TUNNEL_PROVIDER"] ?? "cloudflare") === "cloudflare" && (
            <p className="text-[11px] text-zinc-500">
              {t("cfNote")}
            </p>
          )}
          {(envVars["TUNNEL_PROVIDER"] ?? "cloudflare") === "polling" && (
            <p className="text-[11px] text-zinc-500">
              {t("pollingNote")}
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
          {authMethod === "api_key" ? t("securityNote") : t("securityNoteOAuth")}
        </p>
      </div>

      {/* 추가 환경변수 목록 */}
      {extraEnvVars.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-zinc-700">
            {t("extraVarsTitle")}
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
                {value ? "••••••••" : t("emptyValue")}
              </span>
              <button
                type="button"
                onClick={() => handleRemove(key)}
                aria-label={`${key}`}
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
          {t("addVarTitle")}{" "}
          <span className="text-xs font-normal text-zinc-500">{t("addVarOptional")}</span>
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
            onChange={(e) => setNewValue(sanitizeIntegrationInput(e.target.value))}
            onKeyDown={handleKeyPress}
            placeholder={t("addVarValuePlaceholder")}
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
