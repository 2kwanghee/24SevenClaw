import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import GitHub from "next-auth/providers/github";
import Google from "next-auth/providers/google";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

/** Access Token 만료 5분 전에 갱신 시도 */
const REFRESH_BUFFER_SECONDS = 5 * 60;

/**
 * Refresh Token으로 새 Access Token을 발급받는다.
 */
async function refreshAccessToken(refreshToken: string) {
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) return null;

  const tokens: { access_token: string; refresh_token: string } =
    await res.json();
  return tokens;
}

/**
 * 소셜 로그인 후 백엔드에 사용자 등록/조회하고 JWT 토큰을 발급받는다.
 */
async function syncOAuthUser(profile: {
  provider: string;
  oauthId: string;
  email: string;
  name: string;
  avatarUrl?: string | null;
}) {
  const res = await fetch(`${API_URL}/api/v1/auth/oauth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider: profile.provider,
      oauth_id: profile.oauthId,
      email: profile.email,
      display_name: profile.name,
      avatar_url: profile.avatarUrl,
    }),
  });

  if (!res.ok) return null;

  const tokens = await res.json();

  // 유저 정보 조회
  const meRes = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });

  if (!meRes.ok) return null;

  const user = await meRes.json();

  return {
    id: user.id,
    email: user.email,
    displayName: user.display_name,
    plan: user.plan,
    avatarUrl: user.avatar_url,
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
  };
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  secret: process.env.AUTH_SECRET,
  trustHost: true,
  providers: [
    Credentials({
      credentials: {
        email: { label: "이메일", type: "email" },
        password: { label: "비밀번호", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        // FastAPI 로그인 API 호출
        const loginRes = await fetch(`${API_URL}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password,
          }),
        });

        if (!loginRes.ok) return null;

        const tokens = await loginRes.json();

        // 유저 정보 조회
        const meRes = await fetch(`${API_URL}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${tokens.access_token}` },
        });

        if (!meRes.ok) return null;

        const user = await meRes.json();

        return {
          id: user.id,
          email: user.email,
          displayName: user.display_name,
          plan: user.plan,
          avatarUrl: user.avatar_url,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        };
      },
    }),
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID ?? "",
      clientSecret: process.env.AUTH_GITHUB_SECRET ?? "",
    }),
    Google({
      clientId: process.env.AUTH_GOOGLE_ID ?? "",
      clientSecret: process.env.AUTH_GOOGLE_SECRET ?? "",
    }),
  ],
  callbacks: {
    async signIn({ user, account, profile }) {
      // 소셜 로그인: 백엔드에 사용자 동기화
      if (account?.provider === "github" || account?.provider === "google") {
        const oauthId =
          account.provider === "github"
            ? String(profile?.id ?? account.providerAccountId)
            : account.providerAccountId;

        const result = await syncOAuthUser({
          provider: account.provider,
          oauthId,
          email: user.email ?? profile?.email ?? "",
          name:
            user.name ??
            (profile as Record<string, string>)?.login ??
            "사용자",
          avatarUrl: user.image ?? null,
        });

        if (!result) return false;

        // user 객체에 백엔드 토큰 저장 (jwt 콜백에서 사용)
        user.id = result.id;
        user.accessToken = result.accessToken;
        user.refreshToken = result.refreshToken;
        user.displayName = result.displayName;
        user.plan = result.plan;
        user.avatarUrl = result.avatarUrl;
      }

      return true;
    },
    async jwt({ token, user, account }) {
      // 초기 로그인: 토큰 정보 저장
      if (user) {
        token.accessToken = user.accessToken;
        token.refreshToken = user.refreshToken;
        // Access Token 만료 시간: 30분 (백엔드 설정과 동일)
        token.accessTokenExpires = Date.now() + 30 * 60 * 1000;
        token.displayName = user.displayName;
        token.plan = user.plan;
        token.avatarUrl = user.avatarUrl;
        if (account?.provider === "github" || account?.provider === "google") {
          token.sub = user.id;
        }
        return token;
      }

      // 만료 전이면 기존 토큰 반환
      if (Date.now() < token.accessTokenExpires - REFRESH_BUFFER_SECONDS * 1000) {
        return token;
      }

      // 만료 임박 또는 만료됨: Refresh Token으로 갱신
      const refreshed = await refreshAccessToken(token.refreshToken);
      if (refreshed) {
        token.accessToken = refreshed.access_token;
        token.refreshToken = refreshed.refresh_token;
        token.accessTokenExpires = Date.now() + 30 * 60 * 1000;
        token.error = undefined;
      } else {
        // 갱신 실패: 에러 표시 → 클라이언트에서 로그아웃 처리
        token.error = "RefreshTokenError";
      }

      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.user.id = token.sub ?? "";
      session.user.displayName = token.displayName;
      session.user.plan = token.plan;
      session.user.avatarUrl = token.avatarUrl;
      if (token.error) {
        session.error = token.error;
      }
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
});
