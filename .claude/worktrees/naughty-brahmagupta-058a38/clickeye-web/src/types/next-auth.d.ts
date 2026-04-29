import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    accessToken: string;
    refreshToken: string;
    displayName: string;
    plan: string;
    avatarUrl: string | null;
  }

  interface Session {
    accessToken: string;
    error?: "RefreshTokenError";
    user: {
      id: string;
      email: string;
      displayName: string;
      plan: string;
      avatarUrl: string | null;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string;
    refreshToken: string;
    accessTokenExpires: number;
    displayName: string;
    plan: string;
    avatarUrl: string | null;
    error?: "RefreshTokenError";
  }
}
