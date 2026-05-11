import { API_BASE_URL } from "../config.js";
import {
  loadCredentials,
  saveCredentials,
  isExpired,
  decodeJwtExpiry,
} from "../auth/credentials.js";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

const REQUEST_TIMEOUT_MS = 15_000;

async function refreshTokens(
  refreshToken: string,
  baseUrl: string,
): Promise<TokenResponse> {
  const res = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });
  if (!res.ok) throw new AuthRequiredError();
  return res.json() as Promise<TokenResponse>;
}

export class AuthRequiredError extends Error {
  constructor() {
    super(
      "인증이 필요합니다. `ce login`을 먼저 실행해 주세요.",
    );
    this.name = "AuthRequiredError";
  }
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient {
  constructor(private readonly baseUrl: string = API_BASE_URL) {}

  async request<T>(
    method: string,
    path: string,
    body?: unknown,
    requireAuth = true,
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (requireAuth) {
      let creds = await loadCredentials();
      if (!creds) throw new AuthRequiredError();

      if (isExpired(creds)) {
        try {
          const refreshed = await refreshTokens(
            creds.refresh_token,
            this.baseUrl,
          );
          creds = {
            ...creds,
            access_token: refreshed.access_token,
            refresh_token: refreshed.refresh_token,
            expires_at: decodeJwtExpiry(refreshed.access_token),
          };
          await saveCredentials(creds);
        } catch {
          throw new AuthRequiredError();
        }
      }

      headers["Authorization"] = `Bearer ${creds.access_token}`;
    }

    let res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body != null ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });

    // 401 발생 시 refresh 1회 재시도
    if (res.status === 401 && requireAuth) {
      const creds = await loadCredentials();
      if (creds) {
        try {
          const refreshed = await refreshTokens(
            creds.refresh_token,
            this.baseUrl,
          );
          const newCreds = {
            ...creds,
            access_token: refreshed.access_token,
            refresh_token: refreshed.refresh_token,
            expires_at: decodeJwtExpiry(refreshed.access_token),
          };
          await saveCredentials(newCreds);
          headers["Authorization"] = `Bearer ${newCreds.access_token}`;
          res = await fetch(`${this.baseUrl}${path}`, {
            method,
            headers,
            body: body != null ? JSON.stringify(body) : undefined,
            signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
          });
        } catch {
          throw new AuthRequiredError();
        }
      } else {
        throw new AuthRequiredError();
      }
    }

    if (!res.ok) {
      await this.throwApiError(res);
    }

    const text = await res.text();
    if (!text.trim()) return undefined as T;
    return JSON.parse(text) as T;
  }

  private async throwApiError(res: Response): Promise<never> {
    let detail = `서버 오류 (HTTP ${res.status})`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI 422 validation error: detail은 [{loc, msg, type}] 배열
        detail = (body.detail as { msg?: string }[])
          .map((e) => e.msg ?? JSON.stringify(e))
          .join(", ");
      }
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }

  get<T>(path: string, requireAuth = true): Promise<T> {
    return this.request<T>("GET", path, undefined, requireAuth);
  }

  post<T>(path: string, body?: unknown, requireAuth = true): Promise<T> {
    return this.request<T>("POST", path, body, requireAuth);
  }

  patch<T>(path: string, body?: unknown, requireAuth = true): Promise<T> {
    return this.request<T>("PATCH", path, body, requireAuth);
  }

  delete<T>(path: string, requireAuth = true): Promise<T> {
    return this.request<T>("DELETE", path, undefined, requireAuth);
  }

  /** Binary POST — returns raw Response with full auth+refresh logic. */
  async postRaw(
    path: string,
    body?: unknown,
    timeoutMs = REQUEST_TIMEOUT_MS,
  ): Promise<Response> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    let creds = await loadCredentials();
    if (!creds) throw new AuthRequiredError();

    if (isExpired(creds)) {
      try {
        const refreshed = await refreshTokens(creds.refresh_token, this.baseUrl);
        creds = {
          ...creds,
          access_token: refreshed.access_token,
          refresh_token: refreshed.refresh_token,
          expires_at: decodeJwtExpiry(refreshed.access_token),
        };
        await saveCredentials(creds);
      } catch {
        throw new AuthRequiredError();
      }
    }

    headers["Authorization"] = `Bearer ${creds.access_token}`;

    const doFetch = (token: string) =>
      fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: { ...headers, Authorization: `Bearer ${token}` },
        body: body != null ? JSON.stringify(body) : undefined,
        signal: AbortSignal.timeout(timeoutMs),
      });

    let res = await doFetch(creds.access_token);

    if (res.status === 401) {
      const latestCreds = await loadCredentials();
      if (latestCreds) {
        try {
          const refreshed = await refreshTokens(
            latestCreds.refresh_token,
            this.baseUrl,
          );
          const newCreds = {
            ...latestCreds,
            access_token: refreshed.access_token,
            refresh_token: refreshed.refresh_token,
            expires_at: decodeJwtExpiry(refreshed.access_token),
          };
          await saveCredentials(newCreds);
          res = await doFetch(newCreds.access_token);
        } catch {
          throw new AuthRequiredError();
        }
      } else {
        throw new AuthRequiredError();
      }
    }

    return res;
  }
}

export const apiClient = new ApiClient();
