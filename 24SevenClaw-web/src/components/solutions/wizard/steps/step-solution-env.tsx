"use client";

import { KeyRound, Plus, Trash2, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

export function StepSolutionEnv() {
  const envVars = useSolutionWizardStore((s) => s.data.env.envVars);
  const setEnv = useSolutionWizardStore((s) => s.setEnv);

  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");

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

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-yellow-400" />
        <p className="text-xs text-slate-400">
          환경변수는 ZIP 파일의 <code className="text-yellow-300">.env</code>{" "}
          파일에 저장됩니다. 민감한 정보는 생성 후 직접 수정하는 것을
          권장합니다.
        </p>
      </div>

      {/* 기존 환경변수 목록 */}
      {Object.keys(envVars).length > 0 && (
        <div className="space-y-2">
          {Object.entries(envVars).map(([key, value]) => (
            <div
              key={key}
              className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2"
            >
              <KeyRound className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
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
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 새 환경변수 추가 */}
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
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
