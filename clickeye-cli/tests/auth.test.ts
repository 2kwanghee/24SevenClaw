import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rm, stat } from "node:fs/promises";
import {
  saveCredentials,
  loadCredentials,
  clearCredentials,
  isExpired,
  decodeJwtExpiry,
  type Credentials,
} from "../src/auth/credentials.js";
import { ApiClient, AuthRequiredError, ApiError } from "../src/api/client.js";

// 임시 HOME 디렉토리 — homedir()가 process.env.HOME을 읽으므로 오버라이드
const TEST_HOME = join(tmpdir(), `clickeye-cred-test-${process.pid}`);
const ORIGINAL_HOME = process.env["HOME"];

beforeEach(() => {
  process.env["HOME"] = TEST_HOME;
});

afterEach(async () => {
  process.env["HOME"] = ORIGINAL_HOME;
  await rm(TEST_HOME, { recursive: true, force: true });
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

// ────────────────────────────────────────────────────────
// credentials.ts
// ────────────────────────────────────────────────────────

describe("credentials — 저장/로드/삭제", () => {
  const sample: Credentials = {
    access_token: "tok_access",
    refresh_token: "tok_refresh",
    email: "test@clickeye.ai",
    expires_at: Date.now() + 3600_000,
  };

  it("저장 후 로드하면 동일한 값 반환", async () => {
    await saveCredentials(sample);
    expect(await loadCredentials()).toEqual(sample);
  });

  it("파일 없으면 null 반환", async () => {
    expect(await loadCredentials()).toBeNull();
  });

  it("삭제 후 null 반환", async () => {
    await saveCredentials(sample);
    await clearCredentials();
    expect(await loadCredentials()).toBeNull();
  });

  it("저장 후 파일 퍼미션이 0600", async () => {
    await saveCredentials(sample);
    const credPath = join(TEST_HOME, ".config", "clickeye", "credentials.json");
    const s = await stat(credPath);
    // eslint-disable-next-line no-bitwise
    expect(s.mode & 0o777).toBe(0o600);
  });

  it("재저장해도 파일 퍼미션 0600 유지", async () => {
    await saveCredentials(sample);
    await saveCredentials({ ...sample, access_token: "new_tok" });
    const credPath = join(TEST_HOME, ".config", "clickeye", "credentials.json");
    const s = await stat(credPath);
    // eslint-disable-next-line no-bitwise
    expect(s.mode & 0o777).toBe(0o600);
  });

  it("파일 없어도 clearCredentials 오류 없음", async () => {
    await expect(clearCredentials()).resolves.toBeUndefined();
  });
});

describe("credentials — isExpired", () => {
  const base: Credentials = {
    access_token: "",
    refresh_token: "",
    email: "",
    expires_at: 0,
  };

  it("만료된 토큰 → true", () => {
    expect(isExpired({ ...base, expires_at: Date.now() - 1000 })).toBe(true);
  });

  it("30초 이내 만료 → true (사전 갱신)", () => {
    expect(isExpired({ ...base, expires_at: Date.now() + 20_000 })).toBe(true);
  });

  it("충분히 유효한 토큰 → false", () => {
    expect(isExpired({ ...base, expires_at: Date.now() + 60_000 })).toBe(false);
  });
});

describe("credentials — decodeJwtExpiry", () => {
  it("유효한 JWT exp 클레임 파싱", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
    expect(decodeJwtExpiry(`header.${payload}.sig`)).toBe(exp * 1000);
  });

  it("잘못된 토큰은 1시간 후 fallback 반환", () => {
    const before = Date.now();
    const result = decodeJwtExpiry("bad.token.here");
    expect(result).toBeGreaterThanOrEqual(before + 3590_000);
  });
});

// ────────────────────────────────────────────────────────
// api/client.ts
// ────────────────────────────────────────────────────────

function mockFetchOnce(body: unknown, status = 200): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

describe("ApiClient — requireAuth=false", () => {
  it("Authorization 헤더 없이 요청 전송", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true })),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = new ApiClient("http://localhost:8000");
    await client.post("/api/v1/auth/login", { email: "a@b.com" }, false);

    const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((options.headers as Record<string, string>)["Authorization"]).toBeUndefined();
  });
});

describe("ApiClient — 에러 처리", () => {
  it("credentials 없을 때 401 → AuthRequiredError", async () => {
    mockFetchOnce({ detail: "Unauthorized" }, 401);
    const client = new ApiClient("http://localhost:8000");
    await expect(client.get("/api/v1/me", true)).rejects.toBeInstanceOf(
      AuthRequiredError,
    );
  });

  it("404 응답 시 ApiError(status=404, message=detail 문자열)", async () => {
    mockFetchOnce({ detail: "존재하지 않는 리소스" }, 404);
    const client = new ApiClient("http://localhost:8000");
    try {
      await client.get("/api/v1/missing", false);
      expect.fail("예외가 발생해야 합니다");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).message).toBe("존재하지 않는 리소스");
    }
  });

  it("422 응답 시 ApiError 발생 (detail 배열 → 메시지 조합)", async () => {
    mockFetchOnce(
      {
        detail: [
          { loc: ["body", "email"], msg: "field required", type: "missing" },
          { loc: ["body", "password"], msg: "too short", type: "string_too_short" },
        ],
      },
      422,
    );
    const client = new ApiClient("http://localhost:8000");
    try {
      await client.post("/api/v1/auth/login", {}, false);
      expect.fail("예외가 발생해야 합니다");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(422);
      expect((e as ApiError).message).toContain("field required");
      expect((e as ApiError).message).toContain("too short");
    }
  });

  it("200 응답 JSON 파싱 결과 반환", async () => {
    mockFetchOnce({ id: "abc", name: "테스트" }, 200);
    const client = new ApiClient("http://localhost:8000");
    const result = await client.get<{ id: string; name: string }>(
      "/api/v1/test",
      false,
    );
    expect(result.id).toBe("abc");
    expect(result.name).toBe("테스트");
  });

  it("빈 바디 응답 시 undefined 반환 (200 + 빈 텍스트)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("  ", { status: 200 })),
    );
    const client = new ApiClient("http://localhost:8000");
    const result = await client.delete("/api/v1/item/1", false);
    expect(result).toBeUndefined();
  });
});

describe("ApiClient — 만료된 credentials 자동 갱신", () => {
  it("저장된 토큰이 만료 상태면 refresh 후 재요청", async () => {
    // 만료된 credentials 저장
    await saveCredentials({
      access_token: "old_token",
      refresh_token: "refresh_tok",
      email: "user@test.com",
      expires_at: Date.now() - 1000, // 이미 만료
    });

    const exp = Math.floor(Date.now() / 1000) + 3600;
    const newPayload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
    const newToken = `h.${newPayload}.s`;

    const fetchMock = vi
      .fn()
      // 1st call: refresh endpoint
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: newToken,
            refresh_token: "new_refresh",
          }),
        ),
      )
      // 2nd call: 실제 요청
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ data: "ok" })),
      );

    vi.stubGlobal("fetch", fetchMock);

    const client = new ApiClient("http://localhost:8000");
    const result = await client.get<{ data: string }>("/api/v1/data", true);
    expect(result.data).toBe("ok");
    expect(fetchMock).toHaveBeenCalledTimes(2);

    // refresh 후 저장된 토큰이 새것으로 교체됐는지 확인
    const creds = await loadCredentials();
    expect(creds?.access_token).toBe(newToken);
  });

  it("요청 중 401 수신 시 refresh 후 재요청 (post-request 401-retry path)", async () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
    const freshToken = `h.${payload}.s`;

    // 유효하지 않은(만료 아닌) 토큰으로 저장 — 서버가 401을 내려야 refresh 경로 진입
    await saveCredentials({
      access_token: "seemingly_valid_but_revoked",
      refresh_token: "refresh_tok2",
      email: "user2@test.com",
      expires_at: Date.now() + 60_000, // 만료 안됨 → isExpired 미진입
    });

    const fetchMock = vi
      .fn()
      // 1st call: 실제 요청 → 401
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }),
      )
      // 2nd call: refresh 성공
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ access_token: freshToken, refresh_token: "r2" }),
        ),
      )
      // 3rd call: 재요청 성공
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true })),
      );

    vi.stubGlobal("fetch", fetchMock);

    const client = new ApiClient("http://localhost:8000");
    const result = await client.get<{ ok: boolean }>("/api/v1/data", true);
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(3);

    const creds = await loadCredentials();
    expect(creds?.access_token).toBe(freshToken);
  });

  it("refresh 실패 시 AuthRequiredError 발생", async () => {
    await saveCredentials({
      access_token: "revoked",
      refresh_token: "expired_refresh",
      email: "user3@test.com",
      expires_at: Date.now() - 1000, // 만료 — isExpired 진입
    });

    // refresh endpoint 400 응답
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Refresh token expired" }), {
          status: 400,
        }),
      ),
    );

    const client = new ApiClient("http://localhost:8000");
    await expect(client.get("/api/v1/data", true)).rejects.toBeInstanceOf(
      AuthRequiredError,
    );
  });
});
