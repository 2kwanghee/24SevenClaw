import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { rm, mkdir, writeFile } from "node:fs/promises";
import { INITIAL_WIZARD_STATE, type WizardState } from "../src/wizard/state.js";
import { step11Confirm } from "../src/wizard/steps/11-confirm.js";
import { saveCredentials } from "../src/auth/credentials.js";

// ── 테스트 HOME 격리 ───────────────────────────────────────────────────────────

const TEST_HOME = join(tmpdir(), `ce-wizard-11-test-${process.pid}`);
const ORIGINAL_HOME = process.env["HOME"];

const VALID_CREDS = {
  access_token: "test_token",
  refresh_token: "test_refresh",
  email: "test@clickeye.ai",
  expires_at: Date.now() + 3_600_000,
};

// ── fetch 모킹 ────────────────────────────────────────────────────────────────

type FetchResponse = { body: unknown; status?: number; contentType?: string };

function mockFetchSequence(responses: FetchResponse[]): ReturnType<typeof vi.fn> {
  let callIndex = 0;
  const fetchMock = vi.fn().mockImplementation(() => {
    const resp = responses[callIndex] ?? responses[responses.length - 1];
    callIndex++;
    const ct = resp.contentType ?? "application/json";
    const body =
      ct === "application/zip"
        ? new Uint8Array([0x50, 0x4b, 0x05, 0x06, ...new Array(18).fill(0)]) // minimal ZIP end-of-central-directory
        : JSON.stringify(resp.body);
    return Promise.resolve(
      new Response(body, {
        status: resp.status ?? 200,
        headers: { "Content-Type": ct },
      }),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// ── download.ts 모킹 (unzip 실행 불필요) ─────────────────────────────────────

vi.mock("../src/api/download.js", () => ({
  downloadAndExtract: vi.fn().mockResolvedValue("/tmp/test-project"),
}));

vi.mock("inquirer", () => ({
  default: { prompt: vi.fn() },
}));

// ── 픽스처 ────────────────────────────────────────────────────────────────────

const FULL_STATE: WizardState = {
  ...INITIAL_WIZARD_STATE,
  sessionId: "sess-final-001",
  organizationId: "org-001",
  currentStep: 11,
  company: {
    companyName: "테스트 주식회사",
    industry: "SaaS",
    techStack: ["React", "FastAPI"],
    mainProduct: "AI 플랫폼",
    businessType: "B2B",
    solutionPrompt: "테스트 솔루션",
    enableAutoDecompose: true,
  },
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
    recommendedPMs: [
      {
        pmId: "pm-001",
        name: "김민준",
        slug: "pm-minjun",
        title: "시니어 PM",
        domain: "SaaS",
        matchScore: 0.92,
        reasoning: "적합",
      },
    ],
  },
  agents: {
    selectedAgents: ["agent-1"],
    selectedSkills: ["skill-1", "skill-2"],
    selectedHooks: ["hook-1"],
  },
  platform: { platformId: "plat-aws" },
  os: { osId: "wsl2" },
  env: {
    authMethod: "api_key",
    envVars: {
      ANTHROPIC_API_KEY: "sk-ant-test",
      LINEAR_API_KEY: "lin_api_test",
      LINEAR_TEAM_ID: "team-uuid",
    },
  },
  roi: { result: null },
};

const FINALIZE_RESPONSE = {
  project_id: "proj-abc-123",
  project_name: "테스트-주식회사-solution",
  session_id: "sess-final-001",
  message: "프로젝트가 생성되었습니다",
  initial_task_url: "https://linear.app/team/issue/TEST-1",
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

// ── step11Confirm ─────────────────────────────────────────────────────────────

describe("step11Confirm", () => {
  it("sessionId 없으면 에러 throw", async () => {
    await expect(step11Confirm({ ...INITIAL_WIZARD_STATE })).rejects.toThrow("세션 ID");
  });

  it("POST /finalize 올바른 payload로 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "테스트-프로젝트" })
      .mockResolvedValueOnce({ confirmed: true });

    const fetchMock = mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    await step11Confirm(FULL_STATE);

    const finalizeCall = fetchMock.mock.calls.find(([url]: [string]) =>
      (url as string).includes("/finalize"),
    );
    expect(finalizeCall).toBeDefined();
    const body = JSON.parse((finalizeCall![1] as RequestInit).body as string) as {
      project_name: string;
      hook_ids: string[];
      linear_api_key: string | null;
      linear_team_id: string | null;
    };
    expect(body.project_name).toBe("테스트-프로젝트");
    expect(body.hook_ids).toEqual(["hook-1"]);
    expect(body.linear_api_key).toBe("lin_api_test");
    expect(body.linear_team_id).toBe("team-uuid");
  });

  it("finalize 후 downloadAndExtract 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })
      .mockResolvedValueOnce({ confirmed: true });

    mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    const { downloadAndExtract } = await import("../src/api/download.js");

    await step11Confirm(FULL_STATE);

    expect(downloadAndExtract).toHaveBeenCalledWith(
      FINALIZE_RESPONSE.project_id,
      FULL_STATE.env.envVars,
      FINALIZE_RESPONSE.project_name,
    );
  });

  it("완료 후 currentStep이 12로 증가됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })
      .mockResolvedValueOnce({ confirmed: true });

    mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    const result = await step11Confirm(FULL_STATE);
    expect(result.currentStep).toBe(12);
  });

  it("미확인 시 process.exit(0) 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })
      .mockResolvedValueOnce({ confirmed: false });

    mockFetchSequence([]);

    const exitSpy = vi.spyOn(process, "exit").mockImplementation(() => {
      throw new Error("process.exit called");
    });

    await expect(step11Confirm(FULL_STATE)).rejects.toThrow("process.exit called");
    expect(exitSpy).toHaveBeenCalledWith(0);
    exitSpy.mockRestore();
  });

  it("finalize API 실패 시 에러 throw", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })
      .mockResolvedValueOnce({ confirmed: true });

    mockFetchSequence([{ body: { detail: "서버 오류" }, status: 500 }]);

    await expect(step11Confirm(FULL_STATE)).rejects.toThrow();
  });

  it("default 프로젝트명에 회사명이 포함됨", async () => {
    const inquirer = await import("inquirer");
    const promptMock = vi.mocked(inquirer.default.prompt);
    promptMock
      .mockResolvedValueOnce({ projectName: "테스트-주식회사-solution" })
      .mockResolvedValueOnce({ confirmed: true });

    mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    await step11Confirm(FULL_STATE);

    const firstCall = promptMock.mock.calls[0]!;
    const questions = firstCall[0] as Array<{ name: string; default?: string }>;
    const nameQuestion = questions.find((q) => q.name === "projectName");
    expect(nameQuestion?.default).toContain("테스트");
  });

  it("notion_api_key가 없으면 null로 전송됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })
      .mockResolvedValueOnce({ confirmed: true });

    const fetchMock = mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    const stateNoNotion: WizardState = {
      ...FULL_STATE,
      env: { ...FULL_STATE.env, envVars: { ANTHROPIC_API_KEY: "sk-ant" } },
    };

    await step11Confirm(stateNoNotion);

    const finalizeCall = fetchMock.mock.calls.find(([url]: [string]) =>
      (url as string).includes("/finalize"),
    );
    const body = JSON.parse((finalizeCall![1] as RequestInit).body as string) as {
      notion_api_key: null;
      linear_api_key: null;
    };
    expect(body.notion_api_key).toBeNull();
    expect(body.linear_api_key).toBeNull();
  });

  it("deferredEnvVars 있을 때 finalize 전에 prompt + finalize/download 모두 수집된 값 사용", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })
      .mockResolvedValueOnce({ confirmed: true })
      .mockResolvedValueOnce({ value: "sk-ant-deferred-key" }) // ANTHROPIC_API_KEY
      .mockResolvedValueOnce({ value: "lin_api_deferred" });   // LINEAR_API_KEY

    const fetchMock = mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    const { downloadAndExtract } = await import("../src/api/download.js");

    const stateDeferred: WizardState = {
      ...FULL_STATE,
      env: {
        authMethod: "api_key",
        envVars: {},
        deferredEnvVars: ["ANTHROPIC_API_KEY", "LINEAR_API_KEY"],
      },
    };

    await step11Confirm(stateDeferred);

    // finalize 페이로드에 수집된 LINEAR_API_KEY가 포함되어야 함 (C1 검증)
    const finalizeCall = fetchMock.mock.calls.find(([url]: [string]) =>
      (url as string).includes("/finalize"),
    );
    const body = JSON.parse((finalizeCall![1] as RequestInit).body as string) as {
      linear_api_key: string | null;
    };
    expect(body.linear_api_key).toBe("lin_api_deferred");

    // downloadAndExtract에도 동일한 값이 전달되어야 함
    const callArgs = vi.mocked(downloadAndExtract).mock.calls[0]!;
    expect(callArgs[1]["ANTHROPIC_API_KEY"]).toBe("sk-ant-deferred-key");
    expect(callArgs[1]["LINEAR_API_KEY"]).toBe("lin_api_deferred");
  });

  it("deferredEnvVars 없을 때 추가 prompt 없음", async () => {
    const inquirer = await import("inquirer");
    const promptMock = vi.mocked(inquirer.default.prompt);
    promptMock
      .mockResolvedValueOnce({ projectName: "my-project" })
      .mockResolvedValueOnce({ confirmed: true });

    mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    await step11Confirm(FULL_STATE);

    // prompt 호출: projectName + confirm = 2회만
    expect(promptMock).toHaveBeenCalledTimes(2);
  });

  it("빈 값 입력 후 게이트에서 재입력 시 download 진행됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })   // projectName
      .mockResolvedValueOnce({ confirmed: true })              // confirmed
      .mockResolvedValueOnce({ value: "" })                    // SOME_API_KEY — 빈 입력
      .mockResolvedValueOnce({ action: "enter" })              // 게이트: 지금 입력
      .mockResolvedValueOnce({ value: "secret-value" });       // SOME_API_KEY 재입력

    mockFetchSequence([{ body: FINALIZE_RESPONSE }]);

    const { downloadAndExtract } = await import("../src/api/download.js");

    const stateDeferred: WizardState = {
      ...FULL_STATE,
      env: {
        authMethod: "api_key",
        envVars: {},
        deferredEnvVars: ["SOME_API_KEY"],
      },
    };

    await step11Confirm(stateDeferred);

    // 게이트 통과 후 download 호출되고 수집된 값이 전달되어야 함
    const callArgs = vi.mocked(downloadAndExtract).mock.calls[0]!;
    expect(callArgs[1]["SOME_API_KEY"]).toBe("secret-value");
  });

  it("빈 값 입력 후 게이트에서 취소 시 process.exit(0) 호출됨", async () => {
    const inquirer = await import("inquirer");
    vi.mocked(inquirer.default.prompt)
      .mockResolvedValueOnce({ projectName: "my-project" })   // projectName
      .mockResolvedValueOnce({ confirmed: true })              // confirmed
      .mockResolvedValueOnce({ value: "" })                    // SOME_API_KEY — 빈 입력
      .mockResolvedValueOnce({ action: "cancel" });            // 게이트: 취소

    mockFetchSequence([]);

    const exitSpy = vi.spyOn(process, "exit").mockImplementation(() => {
      throw new Error("process.exit called");
    });

    const stateDeferred: WizardState = {
      ...FULL_STATE,
      env: {
        authMethod: "api_key",
        envVars: {},
        deferredEnvVars: ["SOME_API_KEY"],
      },
    };

    await expect(step11Confirm(stateDeferred)).rejects.toThrow("process.exit called");
    expect(exitSpy).toHaveBeenCalledWith(0);
    exitSpy.mockRestore();
  });
});
