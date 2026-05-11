import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rm } from "node:fs/promises";
import { INITIAL_WIZARD_STATE, type WizardState } from "../src/wizard/state.js";
import { step03PMRecommend } from "../src/wizard/steps/03-pm-recommend.js";
import { step04PMSelect } from "../src/wizard/steps/04-pm-select.js";
import { step05PMComposition } from "../src/wizard/steps/05-pm-composition.js";
import { step06Agents } from "../src/wizard/steps/06-agents.js";
import { saveCredentials } from "../src/auth/credentials.js";
import { clearCatalogCache } from "../src/api/catalog.js";

// ── 테스트 HOME 격리 ───────────────────────────────────────────────────────────

const TEST_HOME = join(tmpdir(), `ce-wizard-36-test-${process.pid}`);
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

const SESSION_STATE: WizardState = {
  ...INITIAL_WIZARD_STATE,
  sessionId: "sess-pm-001",
  organizationId: "org-001",
  currentStep: 3,
  prototypes: {
    selectedPrototypeId: "proto-1",
    prototypes: [],
  },
};

const RECOMMEND_PMS_RESPONSE = {
  items: [
    {
      pm_id: "pm-001",
      name: "김민준",
      slug: "pm-minjun",
      title: "시니어 PM",
      domain: "SaaS / B2B",
      match_score: 0.92,
      reasoning: "B2B SaaS 경험 풍부, 팀 규모에 적합",
    },
    {
      pm_id: "pm-002",
      name: "이서연",
      slug: "pm-seoyeon",
      title: null,
      domain: "모바일",
      match_score: 0.75,
      reasoning: "모바일 분야 강점",
    },
  ],
};

const COMPOSITION_RESPONSE = {
  agents: [
    {
      id: "comp-1",
      component_type: "agent",
      component_slug: "ticket-processor",
      component_name: "티켓 처리 에이전트",
      config: { description: "Jira 티켓을 자동으로 분류합니다" },
      is_required: true,
      display_order: 1,
    },
  ],
  skills: [
    {
      id: "comp-2",
      component_type: "skill",
      component_slug: "jira-reader",
      component_name: "Jira 리더",
      config: {},
      is_required: true,
      display_order: 1,
    },
  ],
  hooks: [],
  mcp_servers: [],
  plugins: [],
};

const CATALOG_AGENTS = [
  { id: "agent-1", slug: "code-reviewer", label: "코드 리뷰 에이전트", category: "agent" },
  { id: "agent-2", slug: "ticket-processor", label: "티켓 처리 에이전트", category: "agent" },
];

const CATALOG_SKILLS = [
  { id: "skill-1", slug: "jira-reader", label: "Jira 리더", category: "ticket_source" },
  { id: "skill-2", slug: "linear-reader", label: "Linear 리더", category: "ticket_source" },
  { id: "skill-3", slug: "slack-notifier", label: "Slack 알림", category: "notification" },
];

const CATALOG_HOOKS = [
  { id: "hook-1", slug: "pr-webhook", label: "PR 웹훅", category: "hook" },
];

vi.mock("inquirer", () => ({
  default: { prompt: vi.fn() },
}));

// ── Setup / Teardown ──────────────────────────────────────────────────────────

beforeEach(async () => {
  process.env["HOME"] = TEST_HOME;
  await saveCredentials(VALID_CREDS);
  clearCatalogCache();
});

afterEach(async () => {
  process.env["HOME"] = ORIGINAL_HOME;
  await rm(TEST_HOME, { recursive: true, force: true });
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  clearCatalogCache();
});

// ── step03PMRecommend ─────────────────────────────────────────────────────────

describe("step03PMRecommend", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(
      step03PMRecommend({ ...INITIAL_WIZARD_STATE }),
    ).rejects.toThrow("세션 ID");
  });

  it("POST /recommend-pms 호출 후 recommendedPMs에 매핑됨", async () => {
    const fetchMock = mockFetchSequence([
      { body: RECOMMEND_PMS_RESPONSE },
    ]);

    const result = await step03PMRecommend(SESSION_STATE);

    const urls = fetchMock.mock.calls.map(([url]: [string]) => url as string);
    expect(urls.some((u) => u.includes("/recommend-pms"))).toBe(true);
    expect(result.pm.recommendedPMs).toHaveLength(2);
  });

  it("snake_case → camelCase 올바르게 매핑됨", async () => {
    mockFetchSequence([{ body: RECOMMEND_PMS_RESPONSE }]);

    const result = await step03PMRecommend(SESSION_STATE);
    const pm = result.pm.recommendedPMs[0]!;
    expect(pm.pmId).toBe("pm-001");
    expect(pm.name).toBe("김민준");
    expect(pm.slug).toBe("pm-minjun");
    expect(pm.title).toBe("시니어 PM");
    expect(pm.domain).toBe("SaaS / B2B");
    expect(pm.matchScore).toBe(0.92);
    expect(pm.reasoning).toBe("B2B SaaS 경험 풍부, 팀 규모에 적합");
  });

  it("null title/domain 허용됨", async () => {
    mockFetchSequence([{ body: RECOMMEND_PMS_RESPONSE }]);

    const result = await step03PMRecommend(SESSION_STATE);
    const pm = result.pm.recommendedPMs[1]!;
    expect(pm.title).toBeNull();
    expect(pm.domain).toBe("모바일");
  });

  it("currentStep이 4로 증가됨", async () => {
    mockFetchSequence([{ body: RECOMMEND_PMS_RESPONSE }]);

    const result = await step03PMRecommend(SESSION_STATE);
    expect(result.currentStep).toBe(4);
  });

  it("API 실패 시 에러 throw", async () => {
    mockFetchSequence([{ body: { detail: "Internal Server Error" }, status: 500 }]);

    await expect(step03PMRecommend(SESSION_STATE)).rejects.toThrow();
  });
});

// ── step04PMSelect ────────────────────────────────────────────────────────────

const STATE_WITH_PMS: WizardState = {
  ...SESSION_STATE,
  currentStep: 4,
  pm: {
    selectedPmProfileId: null,
    recommendedPMs: RECOMMEND_PMS_RESPONSE.items.map((p) => ({
      pmId: p.pm_id,
      name: p.name,
      slug: p.slug,
      title: p.title,
      domain: p.domain,
      matchScore: p.match_score,
      reasoning: p.reasoning,
    })),
  },
};

describe("step04PMSelect", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(
      step04PMSelect({ ...INITIAL_WIZARD_STATE }),
    ).rejects.toThrow("세션 ID");
  });

  it("recommendedPMs 없으면 에러 throw", async () => {
    await expect(
      step04PMSelect({ ...SESSION_STATE, currentStep: 4 }),
    ).rejects.toThrow("추천된 PM이 없습니다");
  });

  it("선택된 PM ID가 PATCH로 전송됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ selectedPmId: "pm-001" });

    const fetchMock = mockFetchSequence([
      { body: { id: SESSION_STATE.sessionId } },
    ]);

    await step04PMSelect(STATE_WITH_PMS);

    const patchCall = fetchMock.mock.calls.find(([, opts]: [string, RequestInit]) =>
      opts.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    const body = JSON.parse((patchCall![1] as RequestInit).body as string) as {
      selected_pm_id: string;
      current_step: number;
    };
    expect(body.selected_pm_id).toBe("pm-001");
    expect(body.current_step).toBe(5);
  });

  it("state에 selectedPmProfileId 반영됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ selectedPmId: "pm-002" });

    mockFetchSequence([{ body: {} }]);

    const result = await step04PMSelect(STATE_WITH_PMS);
    expect(result.pm.selectedPmProfileId).toBe("pm-002");
    expect(result.currentStep).toBe(5);
  });
});

// ── step05PMComposition ───────────────────────────────────────────────────────

const STATE_WITH_SELECTED_PM: WizardState = {
  ...STATE_WITH_PMS,
  currentStep: 5,
  pm: {
    ...STATE_WITH_PMS.pm,
    selectedPmProfileId: "pm-001",
  },
};

describe("step05PMComposition", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(
      step05PMComposition({ ...INITIAL_WIZARD_STATE }),
    ).rejects.toThrow("세션 ID");
  });

  it("selectedPmProfileId 없으면 에러 throw", async () => {
    await expect(
      step05PMComposition({ ...SESSION_STATE, currentStep: 5 }),
    ).rejects.toThrow("선택된 PM이 없습니다");
  });

  it("GET /pm-profiles/{id}/composition 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ confirmed: true });

    const fetchMock = mockFetchSequence([
      { body: COMPOSITION_RESPONSE },
      { body: {} }, // PATCH
    ]);

    await step05PMComposition(STATE_WITH_SELECTED_PM);

    const urls = fetchMock.mock.calls.map(([url]: [string]) => url as string);
    expect(urls.some((u) => u.includes("/pm-profiles/pm-001/composition"))).toBe(true);
  });

  it("확인 후 currentStep이 6으로 증가됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ confirmed: true });

    mockFetchSequence([
      { body: COMPOSITION_RESPONSE },
      { body: {} },
    ]);

    const result = await step05PMComposition(STATE_WITH_SELECTED_PM);
    expect(result.currentStep).toBe(6);
  });

  it("PATCH /prototype-sessions/{sid} with current_step:6 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ confirmed: true });

    const fetchMock = mockFetchSequence([
      { body: COMPOSITION_RESPONSE },
      { body: {} },
    ]);

    await step05PMComposition(STATE_WITH_SELECTED_PM);

    const patchCall = fetchMock.mock.calls.find(([, opts]: [string, RequestInit]) =>
      opts.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    const body = JSON.parse((patchCall![1] as RequestInit).body as string) as {
      current_step: number;
    };
    expect(body.current_step).toBe(6);
  });

  it("미확인 시 process.exit(0) 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ confirmed: false });

    mockFetchSequence([{ body: COMPOSITION_RESPONSE }]);

    const exitSpy = vi.spyOn(process, "exit").mockImplementation(() => {
      throw new Error("process.exit called");
    });

    await expect(step05PMComposition(STATE_WITH_SELECTED_PM)).rejects.toThrow(
      "process.exit called",
    );
    expect(exitSpy).toHaveBeenCalledWith(0);
    exitSpy.mockRestore();
  });
});

// ── step06Agents ──────────────────────────────────────────────────────────────

const STATE_FOR_AGENTS: WizardState = {
  ...STATE_WITH_SELECTED_PM,
  currentStep: 6,
};

describe("step06Agents", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(
      step06Agents({ ...INITIAL_WIZARD_STATE }),
    ).rejects.toThrow("세션 ID");
  });

  it("에이전트 선택 없으면 재시도 후 선택 시 진행됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ agents: [] })           // first agent prompt (empty — retry)
      .mockResolvedValueOnce({ agents: ["agent-1"] })  // second agent prompt
      .mockResolvedValueOnce({ ticketSource: "skill-1" }) // ticket source
      .mockResolvedValueOnce({ additionalSkills: [] })    // additional skills
      .mockResolvedValueOnce({ hooks: [] });              // hooks

    mockFetchSequence([
      { body: { agents: ["agent-1"], skills: ["skill-1"], excluded_agents: [], reasoning: null } }, // recommend-components
      { body: { items: CATALOG_AGENTS, total: CATALOG_AGENTS.length } },   // catalog agents
      { body: { items: CATALOG_SKILLS, total: CATALOG_SKILLS.length } },   // catalog skills
      { body: { items: CATALOG_HOOKS, total: CATALOG_HOOKS.length } },     // catalog hooks
      { body: {} },               // PATCH
    ]);

    const result = await step06Agents(STATE_FOR_AGENTS);
    expect(result.agents.selectedAgents).toEqual(["agent-1"]);
  });

  it("ticket_source 스킬 XOR 선택 — list 프롬프트 사용됨", async () => {
    const inquirer = await import("inquirer");
    const promptMock = vi.mocked(inquirer.default.prompt);
    promptMock
      .mockResolvedValueOnce({ agents: ["agent-1"] })
      .mockResolvedValueOnce({ ticketSource: "skill-1" })
      .mockResolvedValueOnce({ additionalSkills: [] })
      .mockResolvedValueOnce({ hooks: [] });

    mockFetchSequence([
      { body: { agents: [], skills: [], excluded_agents: [], reasoning: null } },
      { body: { items: CATALOG_AGENTS, total: CATALOG_AGENTS.length } },
      { body: { items: CATALOG_SKILLS, total: CATALOG_SKILLS.length } },
      { body: { items: CATALOG_HOOKS, total: CATALOG_HOOKS.length } },
      { body: {} },
    ]);

    await step06Agents(STATE_FOR_AGENTS);

    const calls = promptMock.mock.calls;
    const ticketCall = calls.find(([questions]: [Array<{ type: string; name: string }>]) =>
      questions.some((q) => q.type === "list" && q.name === "ticketSource"),
    );
    expect(ticketCall).toBeDefined();
  });

  it("selectedAgents, selectedSkills, selectedHooks가 state에 반영됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ agents: ["agent-1", "agent-2"] })
      .mockResolvedValueOnce({ ticketSource: "skill-2" })
      .mockResolvedValueOnce({ additionalSkills: ["skill-3"] })
      .mockResolvedValueOnce({ hooks: ["hook-1"] });

    mockFetchSequence([
      { body: { agents: [], skills: [], excluded_agents: [], reasoning: null } },
      { body: { items: CATALOG_AGENTS, total: CATALOG_AGENTS.length } },
      { body: { items: CATALOG_SKILLS, total: CATALOG_SKILLS.length } },
      { body: { items: CATALOG_HOOKS, total: CATALOG_HOOKS.length } },
      { body: {} },
    ]);

    const result = await step06Agents(STATE_FOR_AGENTS);
    expect(result.agents.selectedAgents).toEqual(["agent-1", "agent-2"]);
    expect(result.agents.selectedSkills).toContain("skill-2");
    expect(result.agents.selectedSkills).toContain("skill-3");
    expect(result.agents.selectedHooks).toEqual(["hook-1"]);
    expect(result.currentStep).toBe(7);
  });

  it("PATCH current_step:7 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ agents: ["agent-1"] })
      .mockResolvedValueOnce({ ticketSource: "skill-1" })
      .mockResolvedValueOnce({ additionalSkills: [] })
      .mockResolvedValueOnce({ hooks: [] });

    const fetchMock = mockFetchSequence([
      { body: { agents: [], skills: [], excluded_agents: [], reasoning: null } },
      { body: { items: CATALOG_AGENTS, total: CATALOG_AGENTS.length } },
      { body: { items: CATALOG_SKILLS, total: CATALOG_SKILLS.length } },
      { body: { items: CATALOG_HOOKS, total: CATALOG_HOOKS.length } },
      { body: {} },
    ]);

    await step06Agents(STATE_FOR_AGENTS);

    const patchCall = fetchMock.mock.calls.find(([, opts]: [string, RequestInit]) =>
      opts.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    const body = JSON.parse((patchCall![1] as RequestInit).body as string) as {
      current_step: number;
    };
    expect(body.current_step).toBe(7);
  });

  it("recommend-components 실패해도 계속 진행됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ agents: ["agent-1"] })
      .mockResolvedValueOnce({ ticketSource: "skill-1" })
      .mockResolvedValueOnce({ additionalSkills: [] })
      .mockResolvedValueOnce({ hooks: [] });

    mockFetchSequence([
      { body: { detail: "Not Found" }, status: 404 }, // recommend-components fails
      { body: { items: CATALOG_AGENTS, total: CATALOG_AGENTS.length } },
      { body: { items: CATALOG_SKILLS, total: CATALOG_SKILLS.length } },
      { body: { items: CATALOG_HOOKS, total: CATALOG_HOOKS.length } },
      { body: {} },
    ]);

    const result = await step06Agents(STATE_FOR_AGENTS);
    expect(result.agents.selectedAgents).toEqual(["agent-1"]);
  });

  it("추천 components로 에이전트 체크박스 pre-select됨", async () => {
    const inquirer = await import("inquirer");
    const promptMock = vi.mocked(inquirer.default.prompt);
    promptMock
      .mockResolvedValueOnce({ agents: ["agent-1"] })
      .mockResolvedValueOnce({ ticketSource: "skill-1" })
      .mockResolvedValueOnce({ additionalSkills: [] })
      .mockResolvedValueOnce({ hooks: [] });

    mockFetchSequence([
      { body: { agents: ["agent-1"], skills: ["jira-reader"], excluded_agents: [], reasoning: "테스트 추천 근거" } },
      { body: { items: CATALOG_AGENTS, total: CATALOG_AGENTS.length } },
      { body: { items: CATALOG_SKILLS, total: CATALOG_SKILLS.length } },
      { body: { items: CATALOG_HOOKS, total: CATALOG_HOOKS.length } },
      { body: {} },
    ]);

    await step06Agents(STATE_FOR_AGENTS);

    const agentCall = promptMock.mock.calls[0]!;
    const questions = agentCall[0] as Array<{ choices: Array<{ value: string; checked: boolean }> }>;
    const agentQuestion = questions[0]!;
    const agent1Choice = agentQuestion.choices.find((c) => c.value === "agent-1");
    expect(agent1Choice?.checked).toBe(true);
  });
});
