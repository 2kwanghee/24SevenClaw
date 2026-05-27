import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";
import {
  isLocale,
  localeCookieMaxAge,
  localeCookieName,
  pickLocaleFromAcceptLanguage,
} from "@/i18n/routing";

export default auth((req) => {
  const requestHeaders = new Headers(req.headers);
  requestHeaders.set("x-pathname", req.nextUrl.pathname);

  const res = NextResponse.next({ request: { headers: requestHeaders } });

  if (!req.nextUrl.pathname.startsWith("/admin")) {
    const existing = req.cookies.get(localeCookieName)?.value;
    if (!isLocale(existing)) {
      const detected = pickLocaleFromAcceptLanguage(
        req.headers.get("accept-language"),
      );
      res.cookies.set(localeCookieName, detected, {
        path: "/",
        maxAge: localeCookieMaxAge,
        sameSite: "lax",
      });
    }
  }

  return res;
});

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
