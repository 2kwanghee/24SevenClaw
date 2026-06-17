"use client";

import { Languages } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  isLocale,
  localeCookieMaxAge,
  localeCookieName,
  type Locale,
} from "@/i18n/routing";

const options: { value: Locale; label: string }[] = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "id", label: "Bahasa Indonesia" },
  { value: "ja", label: "日本語" },
];

function writeLocaleCookie(next: Locale) {
  document.cookie =
    `${localeCookieName}=${next}; path=/; max-age=${localeCookieMaxAge}; samesite=lax`;
}

export function LocaleToggle() {
  const router = useRouter();
  const pathname = usePathname();
  const activeLocale = useLocale();
  const tA = useTranslations("common.aria");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (pathname?.startsWith("/admin")) return null;

  const handleSelect = (next: Locale) => {
    setOpen(false);
    if (!isLocale(next) || next === activeLocale) return;
    writeLocaleCookie(next);
    router.refresh();
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={tA("languageToggle")}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 items-center gap-1.5 rounded-xl px-2.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
      >
        <Languages className="h-4 w-4" />
        <span className="text-xs font-medium uppercase">{activeLocale}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-11 z-50 min-w-[140px] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-1 shadow-lg"
        >
          {options.map((option) => {
            const selected = option.value === activeLocale;
            return (
              <button
                key={option.value}
                role="menuitem"
                onClick={() => handleSelect(option.value)}
                className={`flex w-full items-center justify-between px-4 py-2 text-sm transition-colors hover:bg-[var(--bg-hover)] ${
                  selected
                    ? "font-semibold text-[var(--text-primary)]"
                    : "text-[var(--text-secondary)]"
                }`}
              >
                <span>{option.label}</span>
                {selected && <span className="text-xs">✓</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
