"use client";

import { ExternalLink, KeyRound, Plus, Trash2, ShieldCheck, CheckCircle2, XCircle } from "lucide-react";
import { useState } from "react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------
  필수 키 설정 — 항상 필요한 키 + 스킬별 필요 키
------------------------------------------------------------------ */

interface RequiredKeyConfig {
  key: string;
  label: string;
  description: string;
  guideUrl: string;
  guideLabel: string;
}

const ALWAYS_REQUIRED: RequiredKeyConfig[] = [
  {
    key: "ANTHROPIC_API_KEY",
    label: "Anthropic API 키",
    description: "Claude AI 모델 호출에 필요한 인증 키",
    guideUrl: "https://console.anthropic.com",
    guideLabel: "console.anthropic.com",
  },
];

const LINEAR_REQUIRED: RequiredKeyConfig[] = [
  {
    key: "LINEAR_API_KEY",
    label: "Linear API 키",
    description: "Linear 이슈 추적 연동에 필요한 API 토큰",
    guideUrl: "https://linear.app/settings/api",
    guideLabel: "linear.app/settings/api",
  },
  {
    key: "LINEAR_TEAM_ID",
    label: "Linear 팀 ID",
    description: "이슈를 생성할 Linear 팀의 UUID",
    guideUrl: "https://linear.app/settings/api",
    guideLabel: "linear.app/settings/api",
  },
];

function getRequiredKeys(selectedSkills: string[]): RequiredKeyConfig[] {
  const configs = [...ALWAYS_REQUIRED];
  if (selectedSkills.includes("linear")) {
    configs.push(...LINEAR_REQUIRED);
  }
  return configs;
}

/* ------------------------------------------------------------------
  필수 키 행 컴포넌트
------------------------------------------------------------------ */

interface RequiredKeyRowProps {
  config: RequiredKeyConfig;
  value: string;
  onChange: (key: string, value: string) => void;
}

function RequiredKeyRow({ config, value, onChange }: RequiredKeyRowProps) {
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
          ? "border-emerald-500/20 bg-emerald-500/5"
          : "border-red-500/20 bg-red-500/5",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          {isSet ? (
            <CheckCircle2
              className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400"
              aria-hidden="true"
            />
          ) : (
            <XCircle
              className="mt-0.5 h-4 w-4 shrink-0 text-red-400"
              aria-hidden="true"
            />
          )}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <code className="font-mono text-xs font-semibold text-slate-200">
                {config.key}
              </code>
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                  isSet
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "bg-red-500/15 text-red-400",
                )}
              >
                {isSet ? "설정됨" : "필수"}
              </span>
            </div>
            <p className="mt-0.5 text-[11px] text-slate-500">
              {config.description}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
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
          <button
            type="button"
            onClick={() => {
              setDraft(value);
              setIsEditing((v) => !v);
            }}
            className="rounded-md px-2 py-1 text-[11px] font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-300"
          >
            {isEditing ? "취소" : isSet ? "수정" : "입력"}
          </button>
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
            className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs text-white placeholder-slate-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
            aria-label={`${config.label} 입력`}
          />
          <button
            type="button"
            onClick={handleSave}
            disabled={!draft.trim()}
            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
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

export function StepSolutionEnv() {
  const envVars = useSolutionWizardStore((s) => s.data.env.envVars);
  const selectedSkills = useSolutionWizardStore(
    (s) => s.data.agents.selectedSkills,
  );
  const setEnv = useSolutionWizardStore((s) => s.setEnv);

  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");

  const requiredKeys = getRequiredKeys(selectedSkills);
  const missingKeys = requiredKeys.filter(
    (c) => !envVars[c.key]?.trim(),
  );

  const handleRequiredKeyChange = (key: string, value: string) => {
    setEnv({ envVars: { ...envVars, [key]: value } });
  };

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

  const extraEnvVars = Object.entries(envVars).filter(
    ([key]) => !requiredKeys.some((c) => c.key === key),
  );

  return (
    <div className="space-y-6">
      {/* 필수 키 섹션 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-slate-300">
            필수 API 키
            <span className="ml-1.5 text-[11px] font-normal text-slate-500">
              ({requiredKeys.length - missingKeys.length}/{requiredKeys.length} 설정됨)
            </span>
          </h3>
        </div>

        {requiredKeys.map((config) => (
          <RequiredKeyRow
            key={config.key}
            config={config}
            value={envVars[config.key] ?? ""}
            onChange={handleRequiredKeyChange}
          />
        ))}

        {missingKeys.length > 0 && (
          <p
            role="alert"
            className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-400"
          >
            필수 키 {missingKeys.length}개가 미설정 상태입니다. 설정 후 다음 단계로 진행하세요.
          </p>
        )}
      </div>

      {/* 보안 안내 */}
      <div className="flex items-start gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
        <ShieldCheck
          className="mt-0.5 h-4 w-4 shrink-0 text-yellow-400"
          aria-hidden="true"
        />
        <p className="text-xs text-slate-400">
          입력한 키는 ZIP 파일의{" "}
          <code className="text-yellow-300">.env</code>에 저장됩니다.
          ZIP 파일은 공유하지 마세요. 방법을 모르는 경우 ZIP의{" "}
          <code className="text-yellow-300">docs/api-keys/</code> 폴더를 참고하세요.
        </p>
      </div>

      {/* 추가 환경변수 목록 */}
      {extraEnvVars.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-slate-300">
            추가 환경변수
          </h3>
          {extraEnvVars.map(([key, value]) => (
            <div
              key={key}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2"
            >
              <KeyRound
                className="h-3.5 w-3.5 shrink-0 text-emerald-400"
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 font-mono text-xs text-slate-300">
                {key}
              </span>
              <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-500">
                {value ? "••••••••" : "(비어있음)"}
              </span>
              <button
                type="button"
                onClick={() => handleRemove(key)}
                aria-label={`${key} 제거`}
                className="rounded-md p-1 text-slate-600 transition-colors hover:bg-red-500/10 hover:text-red-400"
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 환경변수 추가 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          환경변수 추가{" "}
          <span className="text-xs font-normal text-slate-500">(선택)</span>
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="KEY_NAME"
            className="w-1/3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 font-mono text-sm text-white placeholder-slate-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/20"
          />
          <input
            type="text"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="값 (나중에 입력 가능)"
            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder-slate-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/20"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!newKey.trim()}
            className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
