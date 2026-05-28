"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { Terminal, Zap, Code2, Cpu } from "lucide-react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

const PLATFORM_OPTIONS = [
  {
    id: "claude-code",
    label: "Claude Code",
    icon: Terminal,
    available: true,
  },
  {
    id: "gemini-cli",
    label: "Gemini CLI",
    icon: Zap,
    available: false,
  },
  {
    id: "cursor",
    label: "Cursor",
    icon: Code2,
    available: false,
  },
  {
    id: "codex",
    label: "Codex",
    icon: Cpu,
    available: false,
  },
] as const;

export function StepSolutionPlatform() {
  const t = useTranslations("wizard.step5.platform");

  const platformId = useSolutionWizardStore((s) => s.data.platform.platformId);
  const setPlatform = useSolutionWizardStore((s) => s.setPlatform);
  const pmSupportedPlatforms = useSolutionWizardStore(
    (s) => s.data.pm.pmSupportedPlatforms,
  );

  const hasPmFilter = pmSupportedPlatforms.length > 0;

  const platformDescriptions: Record<string, string> = {
    "claude-code": t("claudeCodeDesc"),
    "gemini-cli": t("geminiCliDesc"),
    "cursor": t("cursorDesc"),
    "codex": t("codexDesc"),
  };

  useEffect(() => {
    if (hasPmFilter) {
      // PM이 단일 플랫폼만 지원하면 자동 선택
      const supportedAndAvailable = PLATFORM_OPTIONS.filter(
        (opt) => opt.available && pmSupportedPlatforms.includes(opt.id),
      );
      if (supportedAndAvailable.length === 1) {
        setPlatform({ platformId: supportedAndAvailable[0].id });
        return;
      }
      // 현재 선택된 플랫폼이 PM 미지원이면 지원 플랫폼 중 첫 번째로 자동 교체
      if (platformId && !pmSupportedPlatforms.includes(platformId)) {
        const first = supportedAndAvailable[0];
        if (first) setPlatform({ platformId: first.id });
      }
    } else if (!platformId) {
      setPlatform({ platformId: "claude-code" });
    }
  }, [hasPmFilter, pmSupportedPlatforms]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-500">{t("description")}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {PLATFORM_OPTIONS.map((opt) => {
          const Icon = opt.icon;
          const isSelected = platformId === opt.id;
          const isPmSupported =
            !hasPmFilter || pmSupportedPlatforms.includes(opt.id);
          const isAvailable = opt.available && isPmSupported;
          const showPmUnsupported = hasPmFilter && !isPmSupported;

          const badgeText = showPmUnsupported
            ? t("notSupportedByPm")
            : opt.id === "claude-code"
              ? "Recommended"
              : "Coming soon";
          const badgeClass = showPmUnsupported
            ? "bg-amber-100 text-amber-600"
            : opt.id === "claude-code"
              ? "bg-emerald-100 text-emerald-600"
              : "bg-zinc-100 text-zinc-500";

          return (
            <button
              key={opt.id}
              type="button"
              disabled={!isAvailable}
              onClick={() => isAvailable && setPlatform({ platformId: opt.id })}
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
              <Icon
                className={`mt-0.5 h-5 w-5 shrink-0 ${isSelected ? "text-emerald-600" : "text-zinc-500"}`}
              />
              <div>
                <p
                  className={`text-sm font-semibold ${isSelected ? "text-zinc-950" : "text-zinc-700"}`}
                >
                  {opt.label}
                </p>
                <p className="mt-0.5 text-xs text-zinc-500">
                  {platformDescriptions[opt.id] ?? ""}
                </p>
              </div>
            </button>
          );
        })}
      </div>
      <p className="text-[11px] text-zinc-500">{t("comingSoonNote")}</p>
    </div>
  );
}
