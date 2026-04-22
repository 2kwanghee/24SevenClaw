"use client";

import { useThemeStore, THEMES, type Theme } from "@/stores/theme-store";

const THEME_BORDER_COLORS: Record<Theme, string> = {
  dark: "#8b5cf6",
  light: "#4338ca",
  blue: "#22d3ee",
  gray: "#6ee7b7",
  rose: "#fda4af",
  amber: "#fcd34d",
};

export function ThemeSwitcher() {
  const { theme, setTheme } = useThemeStore();

  return (
    <div className="flex items-center gap-1" role="group" aria-label="테마 선택">
      {THEMES.map((t) => (
        <button
          key={t.value}
          onClick={() => setTheme(t.value)}
          aria-label={`${t.label} 테마`}
          aria-pressed={theme === t.value}
          title={t.label}
          className={`flex h-6 w-6 items-center justify-center rounded-full transition-all hover:scale-110 focus-visible:outline-2 focus-visible:outline-offset-2 ${
            theme === t.value
              ? "ring-2 ring-offset-1 ring-[var(--nav-active-icon)] ring-offset-[var(--bg-base)] scale-110"
              : "opacity-60 hover:opacity-100"
          }`}
          style={{
            backgroundColor: t.color,
            border: `1.5px solid ${THEME_BORDER_COLORS[t.value]}`,
          }}
        />
      ))}
    </div>
  );
}
