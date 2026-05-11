import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rm, stat, readFile } from "node:fs/promises";
import { INITIAL_WIZARD_STATE, type WizardState } from "../src/wizard/state.js";
import { saveSession, loadSession, deleteSession } from "../src/wizard/session.js";
import { step00Company } from "../src/wizard/steps/00-company.js";
import { step01Generation } from "../src/wizard/steps/01-generation.js";
import { step02PrototypeSelect } from "../src/wizard/steps/02-prototype-select.js";
import { saveCredentials } from "../src/auth/credentials.js";

// ── 테스트 HOME 격리 ───────────────────────────────────────────────────────────

const TEST_HOME = join(tmpdir(), `ce-wizard-test-${process.pid}`);
const ORIGINAL_HOME = process.env["HOME"];

const VALID_CREDS = {
  access_token: "test_token",
  refresh_token: "test_refresh",
  email: "test@clickeye.ai",
  expires_at: Date.now() + 3_600_000,
};

// ── fetch 모킹 헬퍼 ───────────────────────────────────────────────────────────

type FetchResponse = { body: unknown; status?: number };

function mockFetchSequence(responses: FetchResponse[]): ReturnType<typeof vi.fn> {
  let callIndex = 0;
  const fetchMock = vi.fn().mockImplementation(() => {
    const resp = responses[callIndex] ?? responses[responses.length - 1];
    callIndex++;
    return Promise.resolve(
      new Response(JSON.stringify(resp.body), {
        status: resp.status ?? 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// ── 픽스처 ────────────────────────────────────────────────────────────────────

const SAMPLE_STATE: WizardState = {
  ...INITIAL_WIZARD_STATE,
  sessionId: "sess-001",
  organizationId: "org-001",
  currentStep: 0,
};

const PROTOTYPE_LIST = {
  items: [
    {
      id: "proto-1",
      variant_index: 0,
      title: "대시보드형 SaaS",
      description: "분석 중심의 B2B SaaS 솔루션",
      is_recommended: true,
      pros: ["확장성", "대시보드 친화"],
      cons: ["초기 구현 복잡"],
    },
    {
      id: "proto-2",
      variant_index: 1,
      title: "모바일 퍼스트 앱",
      description: "모바일 중심 사용자 경험",
      is_recommended: false,
      pros: ["빠른 출시"],
      cons: ["웹 기능 제한"],
    },
  ],
  total: 2,
};

// ── Setup / Teardown ──────────────────────────────────────────────────────────

beforeEach(async () => {
  process.env["HOME"] = TEST_HOME;
  await saveCredentials(VALID_CREDS);
});

afterEach(async () => {
  process.env["HOME"] = ORIGINAL_HOME;
  await rm(TEST_HOME, { recursive: true, force: true });
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

// ── session.ts ────────────────────────────────────────────────────────────────

describe("session — 저장/로드/삭제", () => {
  it("sessionId 없으면 저장 스킵", async () => {
    await saveSession({ ...INITIAL_WIZARD_STATE }); // sessionId: null
    const sessionDir = join(TEST_HOME, ".config", "clickeye");
    const { readdir } = await import("node:fs/promises");
    const files = await readdir(sessionDir).catch(() => []);
    expect(files.filter((f) => f.startsWith("session-"))).toHaveLength(0);
  });

  it("세션 저장 후 로드 동일값 반환", async () => {
    const state: WizardState = { ...SAMPLE_STATE, currentStep: 2 };
    await saveSession(state);
    const loaded = await loadSession("sess-001");
    expect(loaded).toEqual(state);
  });

  it("세션 파일 퍼미션 0600", async () => {
    await saveSession(SAMPLE_STATE);
    const filePath = join(
      TEST_HOME,
      ".config",
      "clickeye",
      "session-sess-001.json",
    );
    const s = await stat(filePath);
    // eslint-disable-next-line no-bitwise
    expect(s.mode & 0o777).toBe(0o600);
  });

  it("존재하지 않는 세션 → null 반환", async () => {
    expect(await loadSession("nonexistent")).toBeNull();
  });

  it("deleteSession으로 세션 삭제", async () => {
    await saveSession(SAMPLE_STATE);
    await deleteSession("sess-001");
    expect(await loadSession("sess-001")).toBeNull();
  });

  it("deleteSession — 파일 없어도 에러 없음", async () => {
    await expect(deleteSession("ghost-session")).resolves.toBeUndefined();
  });

  it("재저장 시 최신 상태로 갱신됨", async () => {
    await saveSession(SAMPLE_STATE);
    const updated = { ...SAMPLE_STATE, currentStep: 3 };
    await saveSession(updated);
    const loaded = await loadSession("sess-001");
    expect(loaded?.currentStep).toBe(3);
  });
});

// ── step00Company ─────────────────────────────────────────────────────────────

vi.mock("inquirer", () => ({
  default: { prompt: vi.fn() },
}));

describe("step00Company", () => {
  const companyAnswers = {
    companyName: "테스트 회사",
    industry: "SaaS / 소프트웨어",
    techStack: "React, FastAPI, PostgreSQL",
    mainProduct: "AI 솔루션 플랫폼",
    businessType: "B2B",
    solutionPrompt: "팀원 생산성을 극대화하는 AI 어시스턴트 솔루션을 만들고 싶습니다",
    enableAutoDecompose: true,
  };

  beforeEach(async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue(companyAnswers);
  });

  it("organizations.upsert + prototypeSessions.create 호출", async () => {
    const fetchMock = mockFetchSequence([
      { body: { id: "org-abc" } },       // POST /organizations/
      { body: { id: "sess-xyz" } },      // POST /prototype-sessions/
    ]);

    await step00Company({ ...INITIAL_WIZARD_STATE });

    const urls = fetchMock.mock.calls.map(([url]: [string]) => url as string);
    expect(urls.some((u) => u.includes("/organizations/"))).toBe(true);
    expect(urls.some((u) => u.includes("/prototype-sessions/"))).toBe(true);
  });

  it("반환 state에 organizationId + sessionId 포함", async () => {
    mockFetchSequence([
      { body: { id: "org-abc" } },
      { body: { id: "sess-xyz" } },
    ]);

    const result = await step00Company({ ...INITIAL_WIZARD_STATE });
    expect(result.organizationId).toBe("org-abc");
    expect(result.sessionId).toBe("sess-xyz");
    expect(result.currentStep).toBe(1);
  });

  it("techStack이 쉼표로 분리되어 배열로 변환", async () => {
    const fetchMock = mockFetchSequence([
      { body: { id: "org-1" } },
      { body: { id: "sess-1" } },
    ]);

    await step00Company({ ...INITIAL_WIZARD_STATE });

    const orgCall = fetchMock.mock.calls.find(([url]: [string]) =>
      (url as string).includes("/organizations/"),
    );
    const body = JSON.parse((orgCall![1] as RequestInit).body as string) as {
      tech_stack: string[];
    };
    expect(body.tech_stack).toEqual(["React", "FastAPI", "PostgreSQL"]);
  });

  it("company 정보가 state에 올바르게 저장", async () => {
    mockFetchSequence([
      { body: { id: "org-1" } },
      { body: { id: "sess-1" } },
    ]);

    const result = await step00Company({ ...INITIAL_WIZARD_STATE });
    expect(result.company.companyName).toBe("테스트 회사");
    expect(result.company.industry).toBe("SaaS / 소프트웨어");
    expect(result.company.enableAutoDecompose).toBe(true);
  });
});

// ── step01Generation ──────────────────────────────────────────────────────────

describe("step01Generation", () => {
  const stateWithSession: WizardState = {
    ...INITIAL_WIZARD_STATE,
    sessionId: "sess-gen-001",
    organizationId: "org-001",
    currentStep: 1,
  };

  it("sessionId 없으면 에러 throw", async () => {
    await expect(
      step01Generation({ ...INITIAL_WIZARD_STATE }),
    ).rejects.toThrow("세션 ID");
  });

  it("generate → status polling → prototypes 조회 순서로 호출", async () => {
    const fetchMock = mockFetchSequence([
      { body: { message: "started", session_id: "sess-gen-001" } }, // generate
      { body: { status: "generating" } },                           // status poll 1
      { body: { status: "completed" } },                            // status poll 2
      { body: PROTOTYPE_LIST },                                      // prototypes list
    ]);

    const result = await step01Generation(stateWithSession, { pollIntervalMs: 0 });

    const urls = fetchMock.mock.calls.map(([url]: [string]) => url as string);
    expect(urls.some((u) => u.includes("/prototypes/generate"))).toBe(true);
    expect(urls.some((u) => u.includes("/status"))).toBe(true);
    expect(urls.some((u) => u.includes("/prototypes") && !u.includes("/generate"))).toBe(true);
    expect(result.currentStep).toBe(2);
  });

  it("prototypes가 state.prototypes.prototypes에 매핑됨", async () => {
    mockFetchSequence([
      { body: { message: "started" } },
      { body: { status: "completed" } },
      { body: PROTOTYPE_LIST },
    ]);

    const result = await step01Generation(stateWithSession, { pollIntervalMs: 0 });
    expect(result.prototypes.prototypes).toHaveLength(2);
    expect(result.prototypes.prototypes[0]?.id).toBe("proto-1");
    expect(result.prototypes.prototypes[0]?.isRecommended).toBe(true);
    expect(result.prototypes.prototypes[1]?.id).toBe("proto-2");
  });

  it("status=failed → Error throw", async () => {
    mockFetchSequence([
      { body: { message: "started" } },
      { body: { status: "failed" } },
    ]);

    await expect(
      step01Generation(stateWithSession, { pollIntervalMs: 0 }),
    ).rejects.toThrow("생성에 실패했습니다");
  });
});

// ── step02PrototypeSelect ─────────────────────────────────────────────────────

describe("step02PrototypeSelect", () => {
  const stateWithPrototypes: WizardState = {
    ...INITIAL_WIZARD_STATE,
    sessionId: "sess-sel-001",
    organizationId: "org-001",
    currentStep: 2,
    prototypes: {
      selectedPrototypeId: null,
      prototypes: [
        {
          id: "proto-1",
          variantIndex: 0,
          title: "대시보드형",
          description: "B2B 중심",
          isRecommended: true,
          pros: ["확장성"],
          cons: ["복잡"],
        },
        {
          id: "proto-2",
          variantIndex: 1,
          title: "모바일 퍼스트",
          description: null,
          isRecommended: false,
          pros: [],
          cons: [],
        },
      ],
    },
  };

  beforeEach(async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ selectedId: "proto-1" });
  });

  it("sessionId 없으면 에러 throw", async () => {
    await expect(
      step02PrototypeSelect({ ...INITIAL_WIZARD_STATE }),
    ).rejects.toThrow("세션 ID");
  });

  it("prototypes 빈 배열이면 에러 throw", async () => {
    await expect(
      step02PrototypeSelect({ ...INITIAL_WIZARD_STATE, sessionId: "x" }),
    ).rejects.toThrow("프로토타입이 없습니다");
  });

  it("PATCH /prototype-sessions/{id} 호출", async () => {
    const fetchMock = mockFetchSequence([
      { body: { id: "sess-sel-001", selected_prototype_id: "proto-1" } },
    ]);

    await step02PrototypeSelect(stateWithPrototypes);

    const patchCall = fetchMock.mock.calls.find(([, opts]: [string, RequestInit]) =>
      opts.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    const [patchUrl] = patchCall as [string];
    expect(patchUrl).toContain("/prototype-sessions/sess-sel-001");
  });

  it("선택된 proto ID가 state에 반영됨", async () => {
    mockFetchSequence([
      { body: { id: "sess-sel-001" } },
    ]);

    const result = await step02PrototypeSelect(stateWithPrototypes);
    expect(result.prototypes.selectedPrototypeId).toBe("proto-1");
    expect(result.currentStep).toBe(3);
  });

  it("PATCH body에 selected_prototype_id + current_step 포함", async () => {
    const fetchMock = mockFetchSequence([
      { body: { id: "sess-sel-001" } },
    ]);

    await step02PrototypeSelect(stateWithPrototypes);

    const patchCall = fetchMock.mock.calls.find(([, opts]: [string, RequestInit]) =>
      opts.method === "PATCH",
    );
    const body = JSON.parse((patchCall![1] as RequestInit).body as string) as {
      selected_prototype_id: string;
      current_step: number;
    };
    expect(body.selected_prototype_id).toBe("proto-1");
    expect(body.current_step).toBe(3);
  });
});
