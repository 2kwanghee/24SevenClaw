import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rm } from "node:fs/promises";
import { INITIAL_WIZARD_STATE, type WizardState } from "../src/wizard/state.js";
import { step07Platform } from "../src/wizard/steps/07-platform.js";
import { step08Os } from "../src/wizard/steps/08-os.js";
import { step09Env } from "../src/wizard/steps/09-env.js";
import { step10Roi } from "../src/wizard/steps/10-roi.js";
import { saveCredentials } from "../src/auth/credentials.js";
import { clearCatalogCache } from "../src/api/catalog.js";

// ── 테스트 HOME 격리 ───────────────────────────────────────────────────────────

const TEST_HOME = join(tmpdir(), `ce-wizard-710-test-${process.pid}`);
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

const BASE_STATE: WizardState = {
  ...INITIAL_WIZARD_STATE,
  sessionId: "sess-phase5-001",
  organizationId: "org-001",
  currentStep: 7,
  prototypes: {
    selectedPrototypeId: "proto-1",
    prototypes: [
      {
        id: "proto-1",
        variantIndex: 0,
        title: "대시보드형 SaaS",
        description: null,
        isRecommended: true,
        pros: [],
        cons: [],
      },
    ],
  },
  pm: {
    selectedPmProfileId: "pm-001",
    recommendedPMs: [],
  },
  agents: {
    selectedAgents: ["agent-1"],
    selectedSkills: ["skill-jira", "skill-slack"],
    selectedHooks: ["hook-1"],
  },
};

const CATALOG_PLATFORMS = [
  { id: "plat-1", label: "AWS ECS", description: "Amazon ECS Fargate" },
  { id: "plat-2", label: "GCP Cloud Run", description: "Google Cloud Run" },
];

const ROI_RESPONSE = {
  baseline_cost: 24_000_000,
  clickeye_cost: 8_000_000,
  savings: 16_000_000,
  savings_ratio: 0.667,
  baseline_days: 80,
  clickeye_days: 28,
  breakdown: [
    { role_key: "pm", label: "PM", days: 10, rate: 800_000, subtotal: 8_000_000 },
    { role_key: "dev", label: "개발자", days: 40, rate: 400_000, subtotal: 16_000_000 },
  ],
  rates_snapshot: {},
  formula_version: "v2",
};

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

// ── step07Platform ────────────────────────────────────────────────────────────

describe("step07Platform", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(step07Platform({ ...INITIAL_WIZARD_STATE })).rejects.toThrow("세션 ID");
  });

  it("플랫폼 카탈로그 빈 경우 에러 throw", async () => {
    mockFetchSequence([{ body: { items: [], total: 0 } }]);

    await expect(step07Platform(BASE_STATE)).rejects.toThrow("플랫폼 카탈로그가 비어 있습니다");
  });

  it("GET /catalog/platforms 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ platformId: "plat-1" });

    const fetchMock = mockFetchSequence([
      { body: { items: CATALOG_PLATFORMS, total: CATALOG_PLATFORMS.length } },
    ]);

    await step07Platform(BASE_STATE);

    const urls = fetchMock.mock.calls.map(([url]: [string]) => url as string);
    expect(urls.some((u) => u.includes("/catalog/platforms"))).toBe(true);
  });

  it("선택된 platformId가 state에 반영됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ platformId: "plat-2" });

    mockFetchSequence([
      { body: { items: CATALOG_PLATFORMS, total: CATALOG_PLATFORMS.length } },
    ]);

    const result = await step07Platform(BASE_STATE);
    expect(result.platform.platformId).toBe("plat-2");
    expect(result.currentStep).toBe(8);
  });
});

// ── step08Os ──────────────────────────────────────────────────────────────────

describe("step08Os", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(step08Os({ ...INITIAL_WIZARD_STATE })).rejects.toThrow("세션 ID");
  });

  it("확인 후 osId=wsl2, currentStep=9 반환", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ confirmed: true });

    mockFetchSequence([]);

    const result = await step08Os(BASE_STATE);
    expect(result.os.osId).toBe("wsl2");
    expect(result.currentStep).toBe(9);
  });

  it("미확인 시 process.exit(0) 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValue({ confirmed: false });

    const exitSpy = vi.spyOn(process, "exit").mockImplementation(() => {
      throw new Error("process.exit called");
    });

    mockFetchSequence([]);

    await expect(step08Os(BASE_STATE)).rejects.toThrow("process.exit called");
    expect(exitSpy).toHaveBeenCalledWith(0);
    exitSpy.mockRestore();
  });
});

// ── step09Env ─────────────────────────────────────────────────────────────────

const ENV_STATE: WizardState = {
  ...BASE_STATE,
  currentStep: 9,
  agents: {
    ...BASE_STATE.agents,
    selectedSkills: ["skill-1"],
  },
};

const CATALOG_SKILLS_NO_INTEGRATION = [
  {
    id: "skill-1",
    slug: "code-analyzer",
    label: "코드 분석",
    description: "코드 품질 분석",
    category: "analysis",
    env_vars: [],
  },
];

describe("step09Env", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(step09Env({ ...INITIAL_WIZARD_STATE })).rejects.toThrow("세션 ID");
  });

  it("api_key 선택 시 ANTHROPIC_API_KEY가 envVars에 저장됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ authMethod: "api_key" })
      .mockResolvedValueOnce({ apiKey: "sk-ant-test-key" });

    mockFetchSequence([
      { body: { items: CATALOG_SKILLS_NO_INTEGRATION, total: 1 } },
    ]);

    const result = await step09Env(ENV_STATE);
    expect(result.env.authMethod).toBe("api_key");
    expect(result.env.envVars["ANTHROPIC_API_KEY"]).toBe("sk-ant-test-key");
    expect(result.currentStep).toBe(10);
  });

  it("oauth_browser 선택 시 추가 API 키 입력 없음", async () => {
    const inquirer = await import("inquirer");
    const promptMock = vi.mocked(inquirer.default.prompt);
    promptMock.mockResolvedValueOnce({ authMethod: "oauth_browser" });

    mockFetchSequence([
      { body: { items: CATALOG_SKILLS_NO_INTEGRATION, total: 1 } },
    ]);

    const result = await step09Env(ENV_STATE);
    expect(result.env.authMethod).toBe("oauth_browser");
    expect(result.env.envVars["ANTHROPIC_API_KEY"]).toBeUndefined();
    expect(promptMock).toHaveBeenCalledTimes(1);
  });

  it("oauth_setup_token 선택 시 CLAUDE_OAUTH_SETUP_TOKEN 저장됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ authMethod: "oauth_setup_token" })
      .mockResolvedValueOnce({ setupToken: "my-setup-token" });

    mockFetchSequence([
      { body: { items: CATALOG_SKILLS_NO_INTEGRATION, total: 1 } },
    ]);

    const result = await step09Env(ENV_STATE);
    expect(result.env.envVars["CLAUDE_OAUTH_SETUP_TOKEN"]).toBe("my-setup-token");
  });

  it("Linear 스킬 선택 시 Linear 통합 설정 검증됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ authMethod: "oauth_browser" })
      .mockResolvedValueOnce({
        linearApiKey: "lin_api_test123",
        linearTeamId: "team-uuid-001",
      });

    const linearSkillState: WizardState = {
      ...ENV_STATE,
      agents: { ...ENV_STATE.agents, selectedSkills: ["skill-linear"] },
    };

    mockFetchSequence([
      {
        body: {
          items: [
            {
              id: "skill-linear",
              slug: "linear-reader",
              label: "Linear 리더",
              description: "Linear 티켓 읽기",
              category: "ticket_source",
              env_vars: [],
            },
          ],
          total: 1,
        },
      }, // catalog/skills
      { body: { valid: true, message: "Linear 연결 성공" } }, // validate/linear
    ]);

    const result = await step09Env(linearSkillState);
    expect(result.env.envVars["LINEAR_API_KEY"]).toBe("lin_api_test123");
    expect(result.env.envVars["LINEAR_TEAM_ID"]).toBe("team-uuid-001");
  });

  it("Notion 스킬 선택 시 Notion 통합 설정 검증됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ authMethod: "oauth_browser" })
      .mockResolvedValueOnce({
        notionApiKey: "secret_test456",
        notionDatabaseId: "notion-db-uuid",
      });

    const notionSkillState: WizardState = {
      ...ENV_STATE,
      agents: { ...ENV_STATE.agents, selectedSkills: ["skill-notion"] },
    };

    mockFetchSequence([
      {
        body: {
          items: [
            {
              id: "skill-notion",
              slug: "notion-reader",
              label: "Notion 리더",
              description: "Notion 페이지 읽기",
              category: "ticket_source",
              env_vars: [],
            },
          ],
          total: 1,
        },
      }, // catalog/skills
      { body: { valid: true, message: "Notion 연결 성공" } }, // validate/notion
    ]);

    const result = await step09Env(notionSkillState);
    expect(result.env.envVars["NOTION_API_KEY"]).toBe("secret_test456");
    expect(result.env.envVars["NOTION_DATABASE_ID"]).toBe("notion-db-uuid");
  });

  it("Linear 검증 실패 후 재입력 시 통과됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ authMethod: "oauth_browser" })
      .mockResolvedValueOnce({ linearApiKey: "lin_api_bad", linearTeamId: "bad-team" })
      .mockResolvedValueOnce({ linearApiKey: "lin_api_good", linearTeamId: "good-team" });

    const linearSkillState: WizardState = {
      ...ENV_STATE,
      agents: { ...ENV_STATE.agents, selectedSkills: ["skill-linear"] },
    };

    mockFetchSequence([
      {
        body: {
          items: [
            {
              id: "skill-linear",
              slug: "linear-reader",
              label: "Linear 리더",
              description: "",
              category: "ticket_source",
              env_vars: [],
            },
          ],
          total: 1,
        },
      },
      { body: { valid: false, message: "잘못된 API 키" } }, // first validation fails
      { body: { valid: true, message: "성공" } },            // second succeeds
    ]);

    const result = await step09Env(linearSkillState);
    expect(result.env.envVars["LINEAR_API_KEY"]).toBe("lin_api_good");
  });
});

// ── step10Roi ─────────────────────────────────────────────────────────────────

const ROI_STATE: WizardState = {
  ...BASE_STATE,
  currentStep: 10,
  platform: { platformId: "plat-1" },
};

describe("step10Roi", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(step10Roi({ ...INITIAL_WIZARD_STATE })).rejects.toThrow("세션 ID");
  });

  it("POST /roi/calculate 올바른 payload로 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ complexity: "medium" })
      .mockResolvedValueOnce({ confirmed: true });

    const fetchMock = mockFetchSequence([{ body: ROI_RESPONSE }]);

    await step10Roi(ROI_STATE);

    const roiCall = fetchMock.mock.calls.find(([url]: [string]) =>
      (url as string).includes("/roi/calculate"),
    );
    expect(roiCall).toBeDefined();
    const body = JSON.parse((roiCall![1] as RequestInit).body as string) as {
      complexity: string;
      selected_agents_count: number;
      selected_skills_count: number;
      selected_hooks_count: number;
      platform_id: string;
    };
    expect(body.complexity).toBe("medium");
    expect(body.selected_agents_count).toBe(1);
    expect(body.selected_skills_count).toBe(2);
    expect(body.selected_hooks_count).toBe(1);
    expect(body.platform_id).toBe("plat-1");
  });

  it("ROI 결과가 state.roi.result에 저장됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ complexity: "high" })
      .mockResolvedValueOnce({ confirmed: true });

    mockFetchSequence([{ body: ROI_RESPONSE }]);

    const result = await step10Roi(ROI_STATE);
    expect(result.roi.result).toEqual(ROI_RESPONSE);
    expect(result.currentStep).toBe(11);
  });

  it("미확인 시 process.exit(0) 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ complexity: "low" })
      .mockResolvedValueOnce({ confirmed: false });

    mockFetchSequence([{ body: ROI_RESPONSE }]);

    const exitSpy = vi.spyOn(process, "exit").mockImplementation(() => {
      throw new Error("process.exit called");
    });

    await expect(step10Roi(ROI_STATE)).rejects.toThrow("process.exit called");
    expect(exitSpy).toHaveBeenCalledWith(0);
    exitSpy.mockRestore();
  });

  it("ROI API 실패 시 에러 throw", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt).mockResolvedValueOnce({ complexity: "medium" });

    mockFetchSequence([{ body: { detail: "서버 오류" }, status: 500 }]);

    await expect(step10Roi(ROI_STATE)).rejects.toThrow();
  });

  it("solution_type이 선택된 프로토타입 타이틀로 설정됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ complexity: "medium" })
      .mockResolvedValueOnce({ confirmed: true });

    const fetchMock = mockFetchSequence([{ body: ROI_RESPONSE }]);

    await step10Roi(ROI_STATE);

    const roiCall = fetchMock.mock.calls.find(([url]: [string]) =>
      (url as string).includes("/roi/calculate"),
    );
    const body = JSON.parse((roiCall![1] as RequestInit).body as string) as {
      solution_type: string;
    };
    expect(body.solution_type).toBe("대시보드형 SaaS");
  });
});
