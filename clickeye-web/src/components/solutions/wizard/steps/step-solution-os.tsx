"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { MonitorDown, ChevronDown, ChevronUp } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

const OS_OPTIONS = [
  {
    id: "wsl2" as const,
    label: "WSL2 (Ubuntu)",
    available: true,
  },
  {
    id: "windows" as const,
    label: "Windows Native",
    available: false,
  },
  {
    id: "macos" as const,
    label: "macOS",
    available: false,
  },
  {
    id: "linux" as const,
    label: "Linux Native",
    available: false,
  },
] as const;

export function StepSolutionOS() {
  const t = useTranslations("wizard.step5.os");

  const osId = useSolutionWizardStore((s) => s.data.os.osId);
  const setOs = useSolutionWizardStore((s) => s.setOs);
  const [wslGuideOpen, setWslGuideOpen] = useState(false);

  const osDescriptions: Record<string, string> = {
    wsl2: t("wsl2Desc"),
    windows: t("windowsDesc"),
    macos: t("macosDesc"),
    linux: t("linuxDesc"),
  };

  useEffect(() => {
    if (!osId) {
      setOs({ osId: "wsl2" });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">{t("description")}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        {OS_OPTIONS.map((opt) => {
          const isSelected = osId === opt.id;
          const isAvailable = opt.available;

          const badgeText = opt.id === "wsl2" ? "Recommended" : "Coming soon";
          const badgeClass =
            opt.id === "wsl2"
              ? "bg-emerald-100 text-emerald-600"
              : "bg-zinc-100 text-zinc-500";

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
                className={`absolute right-3 top-3 rounded-md px-1.5 py-0.5 text-xs font-medium ${badgeClass}`}
              >
                {badgeText}
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
                <p className="mt-0.5 text-xs text-zinc-500">
                  {osDescriptions[opt.id] ?? ""}
                </p>
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
            {t("wslNotInstalled")}
          </span>
          {wslGuideOpen ? (
            <ChevronUp className="h-4 w-4 text-zinc-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-zinc-500" />
          )}
        </button>

        {wslGuideOpen && (
          <div className="border-t border-zinc-200 px-4 py-3 text-xs text-zinc-500 space-y-2">
            <p>{t("wslGuideDesc")}</p>
            <ol className="list-decimal list-inside space-y-1 text-zinc-500">
              <li>
                {t("wslStep1")}{" "}
                <code className="rounded bg-zinc-100 px-1 text-zinc-700">wsl --install</code>
              </li>
              <li>{t("wslStep2")}</li>
              <li>{t("wslStep3")}</li>
            </ol>
            <a
              href="https://learn.microsoft.com/ko-kr/windows/wsl/install"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block text-emerald-600 underline underline-offset-2 hover:text-emerald-600"
            >
              {t("wslGuideLink")}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
