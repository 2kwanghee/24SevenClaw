"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

const noopSubscribe = () => () => {};

/** SSR=false, 클라이언트 마운트 후=true — setState-in-effect 없이 hydration 안전 */
function useMounted(): boolean {
  return useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
}

const BUTTON_CLASS =
  "flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg-header)]";

export function ThemeSwitcher() {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useTranslations("common.aria");
  const mounted = useMounted();

  if (!mounted) {
    return (
      <button type="button" className={BUTTON_CLASS} aria-hidden="true" tabIndex={-1}>
        <Sun className="h-4 w-4" />
      </button>
    );
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      aria-label={isDark ? t("themeLight") : t("themeDark")}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={BUTTON_CLASS}
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
