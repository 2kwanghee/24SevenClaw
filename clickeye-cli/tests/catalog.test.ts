import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rm } from "node:fs/promises";
import {
  fetchAgents,
  fetchSkills,
  fetchHooks,
  fetchPlatforms,
  fetchPipelines,
  fetchCatalog,
  clearCatalogCache,
  type CatalogAgent,
  type CatalogSkill,
  type CatalogHook,
  type CatalogPlatform,
  type CatalogPipeline,
} from "../src/api/catalog.js";
import { AuthRequiredError, ApiError } from "../src/api/client.js";
import { saveCredentials } from "../src/auth/credentials.js";

// ── 테스트 HOME (credentials 격리) ────────────────────────────────────────────

const TEST_HOME = join(tmpdir(), `clickeye-catalog-test-${process.pid}`);
const ORIGINAL_HOME = process.env["HOME"];

const VALID_CREDS = {
  access_token: "test_token",
  refresh_token: "test_refresh",
  email: "test@clickeye.ai",
  expires_at: Date.now() + 3600_000,
};

// ── 헬퍼 ──────────────────────────────────────────────────────────────────────

function mockFetch(body: unknown, status = 200): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// 픽스처 데이터
const sampleAgents: CatalogAgent[] = [
  { id: "ag1", slug: "claude-code", label: "Claude Code", description: "코드 작성 에이전트" },
  { id: "ag2", slug: "gemini", label: "Gemini CLI", description: "Gemini 에이전트" },
];
const sampleSkills: CatalogSkill[] = [
  { id: "sk1", slug: "linear-sync", label: "Linear Sync", description: "Linear 연동" },
];
const sampleHooks: CatalogHook[] = [
  { id: "hk1", slug: "pre-push", label: "Pre Push Hook", description: "Push 전 검증" },
];
const samplePlatforms: CatalogPlatform[] = [
  { id: "pl1", label: "WSL2" },
  { id: "pl2", label: "macOS" },
];
const samplePipelines: CatalogPipeline[] = [
  { id: "pp1", label: "기본 파이프라인" },
];

// ── Setup / Teardown ──────────────────────────────────────────────────────────

beforeEach(async () => {
  process.env["HOME"] = TEST_HOME;
  clearCatalogCache();
  await saveCredentials(VALID_CREDS);
});

afterEach(async () => {
  process.env["HOME"] = ORIGINAL_HOME;
  await rm(TEST_HOME, { recursive: true, force: true });
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  clearCatalogCache();
});

// ── 카테고리별 fetch ──────────────────────────────────────────────────────────

describe("fetchAgents", () => {
  it("agents 목록 반환", async () => {
    mockFetch({ items: sampleAgents, total: 2 });
    const result = await fetchAgents();
    expect(result).toEqual(sampleAgents);
  });

  it("올바른 엔드포인트 호출", async () => {
    const fetchMock = mockFetch({ items: [], total: 0 });
    await fetchAgents();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/api/v1/catalog/agents");
  });
});

describe("fetchSkills", () => {
  it("skills 목록 반환", async () => {
    mockFetch({ items: sampleSkills, total: 1 });
    const result = await fetchSkills();
    expect(result).toEqual(sampleSkills);
  });

  it("올바른 엔드포인트 호출", async () => {
    const fetchMock = mockFetch({ items: [], total: 0 });
    await fetchSkills();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/api/v1/catalog/skills");
  });
});

describe("fetchHooks", () => {
  it("hooks 목록 반환", async () => {
    mockFetch({ items: sampleHooks, total: 1 });
    const result = await fetchHooks();
    expect(result).toEqual(sampleHooks);
  });

  it("올바른 엔드포인트 호출", async () => {
    const fetchMock = mockFetch({ items: [], total: 0 });
    await fetchHooks();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/api/v1/catalog/hooks");
  });
});

describe("fetchPlatforms", () => {
  it("platforms 목록 반환", async () => {
    mockFetch({ items: samplePlatforms, total: 2 });
    const result = await fetchPlatforms();
    expect(result).toEqual(samplePlatforms);
  });

  it("올바른 엔드포인트 호출", async () => {
    const fetchMock = mockFetch({ items: [], total: 0 });
    await fetchPlatforms();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/api/v1/catalog/platforms");
  });
});

describe("fetchPipelines", () => {
  it("pipelines 목록 반환", async () => {
    mockFetch({ items: samplePipelines, total: 1 });
    const result = await fetchPipelines();
    expect(result).toEqual(samplePipelines);
  });

  it("올바른 엔드포인트 호출", async () => {
    const fetchMock = mockFetch({ items: [], total: 0 });
    await fetchPipelines();
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/api/v1/catalog/pipelines");
  });
});

// ── 인메모리 캐시 ────────────────────────────────────────────────────────────

describe("catalog cache", () => {
  it("같은 카테고리 두 번 호출 시 fetch 1회만 실행", async () => {
    const fetchMock = mockFetch({ items: sampleAgents, total: 2 });
    await fetchAgents();
    await fetchAgents();
    // 첫 번째 호출만 실제 fetch (auth Bearer 헤더 포함), 두 번째는 캐시 반환
    // fetch는 1번만 불림
    const catalogCalls = fetchMock.mock.calls.filter(([url]: [string]) =>
      (url as string).includes("/catalog/"),
    );
    expect(catalogCalls).toHaveLength(1);
  });

  it("clearCatalogCache 후 재요청 시 fetch 다시 실행", async () => {
    const fetchMock = mockFetch({ items: sampleAgents, total: 2 });
    await fetchAgents();
    clearCatalogCache();
    await fetchAgents();
    const catalogCalls = fetchMock.mock.calls.filter(([url]: [string]) =>
      (url as string).includes("/catalog/"),
    );
    expect(catalogCalls).toHaveLength(2);
  });

  it("캐시 TTL 만료 시 재요청", async () => {
    let fakeNow = Date.now();
    vi.spyOn(Date, "now").mockImplementation(() => fakeNow);

    const fetchMock = mockFetch({ items: sampleAgents, total: 2 });

    await fetchAgents();

    // 6분 후로 이동 (TTL 5분 초과)
    fakeNow += 6 * 60 * 1000;

    await fetchAgents();

    const catalogCalls = fetchMock.mock.calls.filter(([url]: [string]) =>
      (url as string).includes("/catalog/"),
    );
    expect(catalogCalls).toHaveLength(2);
  });

  it("카테고리별로 캐시가 독립적", async () => {
    const fetchMock = mockFetch({ items: sampleSkills, total: 1 });

    await fetchSkills();
    await fetchSkills(); // 두 번째는 캐시

    const skillCalls = fetchMock.mock.calls.filter(([url]: [string]) =>
      (url as string).includes("/catalog/skills"),
    );
    expect(skillCalls).toHaveLength(1);
  });
});

// ── fetchCatalog 디스패처 ─────────────────────────────────────────────────────

describe("fetchCatalog", () => {
  it("agents 카테고리 → fetchAgents 결과 반환", async () => {
    mockFetch({ items: sampleAgents, total: 2 });
    const result = await fetchCatalog("agents");
    expect(result).toEqual(sampleAgents);
  });

  it("skills 카테고리 → fetchSkills 결과 반환", async () => {
    mockFetch({ items: sampleSkills, total: 1 });
    const result = await fetchCatalog("skills");
    expect(result).toEqual(sampleSkills);
  });

  it("hooks 카테고리 → fetchHooks 결과 반환", async () => {
    mockFetch({ items: sampleHooks, total: 1 });
    const result = await fetchCatalog("hooks");
    expect(result).toEqual(sampleHooks);
  });

  it("platforms 카테고리 → fetchPlatforms 결과 반환", async () => {
    mockFetch({ items: samplePlatforms, total: 2 });
    const result = await fetchCatalog("platforms");
    expect(result).toEqual(samplePlatforms);
  });

  it("pipelines 카테고리 → fetchPipelines 결과 반환", async () => {
    mockFetch({ items: samplePipelines, total: 1 });
    const result = await fetchCatalog("pipelines");
    expect(result).toEqual(samplePipelines);
  });
});

// ── 에러 처리 ─────────────────────────────────────────────────────────────────

describe("catalog error handling", () => {
  it("credentials 없을 때 → AuthRequiredError", async () => {
    // HOME을 비워서 credentials 없도록
    process.env["HOME"] = join(tmpdir(), `empty-${Date.now()}`);
    await expect(fetchAgents()).rejects.toBeInstanceOf(AuthRequiredError);
  });

  it("500 응답 → ApiError(status=500)", async () => {
    mockFetch({ detail: "Internal Server Error" }, 500);
    try {
      await fetchSkills();
      expect.fail("예외가 발생해야 합니다");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(500);
    }
  });

  it("빈 items 배열 → 빈 배열 반환", async () => {
    mockFetch({ items: [], total: 0 });
    const result = await fetchCatalog("agents");
    expect(result).toEqual([]);
  });
});
