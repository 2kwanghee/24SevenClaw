"use client";

import { useEffect } from "react";
import { useLocale } from "next-intl";
import { z } from "zod";

import { isLocale } from "@/i18n/routing";

export function ZodLocaleProvider({ children }: { children: React.ReactNode }) {
  const locale = useLocale();

  useEffect(() => {
    if (!isLocale(locale)) return;
    const localeFactory = z.locales[locale];
    if (typeof localeFactory !== "function") return;
    z.config({ localeError: localeFactory().localeError });
  }, [locale]);

  return <>{children}</>;
}
