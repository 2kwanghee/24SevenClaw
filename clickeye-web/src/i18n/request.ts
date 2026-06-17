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
  // 한국어는 자체 완전 번역본을 그대로 사용한다.
  const ko = (await import("../../messages/ko.json")).default as Messages;
  if (locale === "ko") return ko;

  // 그 외 언어는 en을 폴백 베이스로 깔고 해당 언어를 상위 병합한다.
  // (네임스페이스 누락 시 영어로 안전하게 폴백)
  const en = (await import("../../messages/en.json")).default as Messages;
  if (locale === "en") return en;
  if (locale === "id") {
    const id = (await import("../../messages/id.json")).default as Messages;
    return { ...en, ...id };
  }
  if (locale === "ja") {
    const ja = (await import("../../messages/ja.json")).default as Messages;
    return { ...en, ...ja };
  }
  return en;
}

export default getRequestConfig(async () => {
  const locale = await detectLocale();
  const messages = await loadMessages(locale);
  return {
    locale: locale ?? defaultLocale,
    messages,
  };
});
