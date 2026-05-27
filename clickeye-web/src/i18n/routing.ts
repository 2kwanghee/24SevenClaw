export const locales = ["ko", "en"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";
export const adminLocale: Locale = "ko";

export const localeCookieName = "clickeye-locale";
export const localeCookieMaxAge = 60 * 60 * 24 * 365;

export function isLocale(value: string | undefined | null): value is Locale {
  return value === "ko" || value === "en";
}

export function pickLocaleFromAcceptLanguage(header: string | null | undefined): Locale {
  if (!header) return defaultLocale;
  for (const part of header.split(",")) {
    const tag = part.split(";")[0]?.trim().toLowerCase();
    if (!tag) continue;
    if (tag.startsWith("ko")) return "ko";
    if (tag.startsWith("en")) return "en";
  }
  return defaultLocale;
}
