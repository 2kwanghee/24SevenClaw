"use client";

import { useEffect, useState } from "react";
import { MonitorDown, ChevronDown, ChevronUp } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

const OS_OPTIONS = [
  {
    id: "wsl2" as const,
    label: "WSL2 (Ubuntu)",
    description: "Windows Subsystem for Linux 2 — Claude Code 공식 권장 환경",
    badge: "추천",
    available: true,
  },
  {
    id: "windows" as const,
    label: "Windows 네이티브",
    description: "PowerShell / cmd 직접 실행",
    badge: "Coming soon",
    available: false,
  },
  {
    id: "macos" as const,
    label: "macOS",
    description: "zsh / bash 터미널",
    badge: "Coming soon",
    available: false,
  },
  {
    id: "linux" as const,
    label: "Linux 네이티브",
    description: "Ubuntu · Debian · Fedora 등",
    badge: "Coming soon",
    available: false,
  },
] as const;

export function StepSolutionOS() {
  const osId = useSolutionWizardStore((s) => s.data.os.osId);
  const setOs = useSolutionWizardStore((s) => s.setOs);
  const [wslGuideOpen, setWslGuideOpen] = useState(false);

  useEffect(() => {
    if (!osId) {
      setOs({ osId: "wsl2" });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">
        ZIP을 압축 해제하고 실행할 OS 환경을 선택하세요. 선택한 환경에 맞는 런처 스크립트가 포함됩니다.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        {OS_OPTIONS.map((opt) => {
          const isSelected = osId === opt.id;
          const isAvailable = opt.available;

          return (
            <button
              key={opt.id}
              type="button"
              disabled={!isAvailable}
              onClick={() => isAvailable && setOs({ osId: opt.id })}
              aria-pressed={isSelected}
              className={`relative flex items-start gap-3 rounded-xl border p-4 text-left transition-all duration-200 ${
                !isAvailable
                  ? "cursor-not-allowed border-zinc-100 bg-zinc-50 opacity-40"
                  : isSelected
                    ? "border-zinc-900 bg-zinc-50 ring-2 ring-zinc-900/10"
                    : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50"
              }`}
            >
              <span
                className={`absolute right-3 top-3 rounded-md px-1.5 py-0.5 text-xs font-medium ${
                  opt.badge === "추천"
                    ? "bg-emerald-100 text-emerald-600"
                    : "bg-zinc-100 text-zinc-500"
                }`}
              >
                {opt.badge}
              </span>
              <MonitorDown
                className={`mt-0.5 h-5 w-5 shrink-0 ${isSelected ? "text-emerald-600" : "text-zinc-500"}`}
              />
              <div>
                <p
                  className={`text-sm font-semibold ${isSelected ? "text-zinc-950" : "text-zinc-700"}`}
                >
                  {opt.label}
                </p>
                <p className="mt-0.5 text-xs text-zinc-500">{opt.description}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* WSL2 미설치 안내 (접힌 패널) */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50">
        <button
          type="button"
          onClick={() => setWslGuideOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
        >
          <span className="text-xs font-medium text-zinc-700">
            WSL2가 설치되어 있지 않으신가요?
          </span>
          {wslGuideOpen ? (
            <ChevronUp className="h-4 w-4 text-zinc-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-zinc-500" />
          )}
        </button>

        {wslGuideOpen && (
          <div className="border-t border-zinc-200 px-4 py-3 text-xs text-zinc-500 space-y-2">
            <p>WSL2는 Windows에서 Linux 환경을 실행할 수 있는 Microsoft 공식 기능입니다.</p>
            <ol className="list-decimal list-inside space-y-1 text-zinc-500">
              <li>
                PowerShell (관리자)에서 실행:{" "}
                <code className="rounded bg-zinc-100 px-1 text-zinc-700">wsl --install</code>
              </li>
              <li>PC 재시작 후 Ubuntu 앱 실행</li>
              <li>사용자 이름 · 비밀번호 설정 후 완료</li>
            </ol>
            <a
              href="https://learn.microsoft.com/ko-kr/windows/wsl/install"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block text-emerald-600 underline underline-offset-2 hover:text-emerald-600"
            >
              공식 설치 가이드 열기 →
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
