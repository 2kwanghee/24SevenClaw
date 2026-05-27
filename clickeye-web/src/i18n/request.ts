import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import {
  adminLocale,
  defaultLocale,
  isLocale,
  localeCookieName,
  pickLocaleFromAcceptLanguage,
  type Locale,
} from "./routing";

async function detectLocale(): Promise<Locale> {
  const h = await headers();
  const pathname = h.get("x-pathname") ?? "";
  if (pathname.startsWith("/admin")) return adminLocale;

  const c = await cookies();
  const cookieValue = c.get(localeCookieName)?.value;
  if (isLocale(cookieValue)) return cookieValue;

  return pickLocaleFromAcceptLanguage(h.get("accept-language"));
}

type Messages = Record<string, unknown>;

async function loadMessages(locale: Locale): Promise<Messages> {
  const ko = (await import("../../messages/ko.json")).default as Messages;
  if (locale === "ko") return ko;
  const en = (await import("../../messages/en.json")).default as Messages;
  return { ...ko, ...en };
}

export default getRequestConfig(async () => {
  const locale = await detectLocale();
  const messages = await loadMessages(locale);
  return {
    locale: locale ?? defaultLocale,
    messages,
  };
});
