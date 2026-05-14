// src/cli.ts
import { Command } from "commander";

// src/commands/init.ts
import chalk13 from "chalk";
import inquirer11 from "inquirer";

// src/wizard/state.ts
var INITIAL_WIZARD_STATE = {
  sessionId: null,
  organizationId: null,
  currentStep: 0,
  company: {
    companyName: "",
    industry: "",
    techStack: [],
    mainProduct: "",
    businessType: "",
    solutionPrompt: "",
    enableAutoDecompose: true
  },
  prototypes: {
    selectedPrototypeId: null,
    prototypes: []
  },
  pm: {
    selectedPmProfileId: null,
    recommendedPMs: []
  },
  agents: {
    selectedAgents: [],
    selectedSkills: [],
    selectedHooks: []
  },
  platform: { platformId: null },
  os: { osId: null },
  env: {
    authMethod: null,
    envVars: {}
  },
  roi: { result: null }
};

// src/wizard/session.ts
import { readFile, writeFile, mkdir, unlink, readdir, stat } from "fs/promises";
import { join } from "path";
import { homedir } from "os";
function sessionDir() {
  return join(homedir(), ".config", "clickeye");
}
function sessionFile(sessionId) {
  return join(sessionDir(), `session-${sessionId}.json`);
}
async function saveSession(state) {
  if (!state.sessionId) return;
  const dir = sessionDir();
  const file = sessionFile(state.sessionId);
  await mkdir(dir, { recursive: true, mode: 448 });
  await writeFile(file, JSON.stringify(state, null, 2), {
    encoding: "utf-8",
    mode: 384
  });
}
async function loadSession(sessionId) {
  let raw;
  try {
    raw = await readFile(sessionFile(sessionId), "utf-8");
  } catch (err) {
    if (err.code === "ENOENT") return null;
    throw new Error(
      `\uC138\uC158 \uD30C\uC77C\uC744 \uC77D\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4: ${String(err)}
\uC138\uC158 \uD30C\uC77C\uC774 \uC190\uC0C1\uB418\uC5C8\uC744 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uC0AD\uC81C \uD6C4 \uC0C8\uB85C \uC2DC\uC791\uD558\uC138\uC694:
  rm ${sessionFile(sessionId)}`
    );
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(
      `\uC138\uC158 \uD30C\uC77C\uC774 \uC190\uC0C1\uB418\uC5C8\uC2B5\uB2C8\uB2E4 (JSON \uD30C\uC2F1 \uC2E4\uD328).
\uC0AD\uC81C \uD6C4 \uC0C8\uB85C \uC2DC\uC791\uD558\uC138\uC694:
  rm ${sessionFile(sessionId)}`
    );
  }
}
async function deleteSession(sessionId) {
  try {
    await unlink(sessionFile(sessionId));
  } catch {
  }
}
async function listSessions() {
  const dir = sessionDir();
  let entries;
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }
  const summaries = [];
  for (const entry of entries) {
    const match = entry.match(/^session-(.+)\.json$/);
    if (!match) continue;
    const sessionId = match[1];
    const filePath = join(dir, entry);
    try {
      const [raw, fileStat] = await Promise.all([
        readFile(filePath, "utf-8"),
        stat(filePath)
      ]);
      const parsed = JSON.parse(raw);
      summaries.push({
        sessionId,
        companyName: parsed.company?.companyName || null,
        currentStep: parsed.currentStep ?? 0,
        savedAt: fileStat.mtime,
        mtime: fileStat.mtime.getTime()
      });
    } catch {
    }
  }
  return summaries.sort((a, b) => b.mtime - a.mtime).map(({ mtime: _mtime, ...rest }) => rest);
}

// src/wizard/steps/00-company.ts
import inquirer from "inquirer";
import chalk from "chalk";

// src/config.ts
var API_BASE_URL = process.env["CLICKEYE_API_URL"] ?? "https://api.clickeye.ai";

// src/auth/credentials.ts
import { readFile as readFile2, writeFile as writeFile2, unlink as unlink2, mkdir as mkdir2, chmod } from "fs/promises";
import { homedir as homedir2 } from "os";
import { join as join2 } from "path";
function credDir() {
  return join2(homedir2(), ".config", "clickeye");
}
function credFile() {
  return join2(credDir(), "credentials.json");
}
async function loadCredentials() {
  try {
    const raw = await readFile2(credFile(), "utf8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
async function saveCredentials(creds) {
  await mkdir2(credDir(), { recursive: true, mode: 448 });
  await writeFile2(credFile(), JSON.stringify(creds, null, 2), {
    encoding: "utf8",
    mode: 384
  });
  await chmod(credFile(), 384);
}
async function clearCredentials() {
  try {
    await unlink2(credFile());
  } catch {
  }
}
function isExpired(creds) {
  return Date.now() >= creds.expires_at - 3e4;
}
function decodeJwtExpiry(token) {
  try {
    const payload = token.split(".")[1];
    if (!payload) return Date.now() + 36e5;
    const decoded = JSON.parse(
      Buffer.from(payload, "base64url").toString("utf8")
    );
    return (decoded.exp ?? 0) * 1e3;
  } catch {
    return Date.now() + 36e5;
  }
}

// src/api/client.ts
var REQUEST_TIMEOUT_MS = 15e3;
async function refreshTokens(refreshToken, baseUrl) {
  const res = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  });
  if (!res.ok) throw new AuthRequiredError();
  return res.json();
}
var AuthRequiredError = class extends Error {
  constructor() {
    super(
      "\uC778\uC99D\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. `ce login`\uC744 \uBA3C\uC800 \uC2E4\uD589\uD574 \uC8FC\uC138\uC694."
    );
    this.name = "AuthRequiredError";
  }
};
var ApiError = class extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
  status;
};
var ApiClient = class {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }
  baseUrl;
  async request(method, path2, body, requireAuth = true) {
    const headers = {
      "Content-Type": "application/json"
    };
    if (requireAuth) {
      let creds = await loadCredentials();
      if (!creds) throw new AuthRequiredError();
      if (isExpired(creds)) {
        try {
          const refreshed = await refreshTokens(
            creds.refresh_token,
            this.baseUrl
          );
          creds = {
            ...creds,
            access_token: refreshed.access_token,
            refresh_token: refreshed.refresh_token,
            expires_at: decodeJwtExpiry(refreshed.access_token)
          };
          await saveCredentials(creds);
        } catch {
          throw new AuthRequiredError();
        }
      }
      headers["Authorization"] = `Bearer ${creds.access_token}`;
    }
    let res = await fetch(`${this.baseUrl}${path2}`, {
      method,
      headers,
      body: body != null ? JSON.stringify(body) : void 0,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    });
    if (res.status === 401 && requireAuth) {
      const creds = await loadCredentials();
      if (creds) {
        try {
          const refreshed = await refreshTokens(
            creds.refresh_token,
            this.baseUrl
          );
          const newCreds = {
            ...creds,
            access_token: refreshed.access_token,
            refresh_token: refreshed.refresh_token,
            expires_at: decodeJwtExpiry(refreshed.access_token)
          };
          await saveCredentials(newCreds);
          headers["Authorization"] = `Bearer ${newCreds.access_token}`;
          res = await fetch(`${this.baseUrl}${path2}`, {
            method,
            headers,
            body: body != null ? JSON.stringify(body) : void 0,
            signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
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
    if (!text.trim()) return void 0;
    return JSON.parse(text);
  }
  async throwApiError(res) {
    let detail = `\uC11C\uBC84 \uC624\uB958 (HTTP ${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((e) => e.msg ?? JSON.stringify(e)).join(", ");
      }
    } catch {
    }
    throw new ApiError(res.status, detail);
  }
  get(path2, requireAuth = true) {
    return this.request("GET", path2, void 0, requireAuth);
  }
  post(path2, body, requireAuth = true) {
    return this.request("POST", path2, body, requireAuth);
  }
  patch(path2, body, requireAuth = true) {
    return this.request("PATCH", path2, body, requireAuth);
  }
  delete(path2, requireAuth = true) {
    return this.request("DELETE", path2, void 0, requireAuth);
  }
  /** Binary POST — returns raw Response with full auth+refresh logic. */
  async postRaw(path2, body, timeoutMs = REQUEST_TIMEOUT_MS) {
    const headers = {
      "Content-Type": "application/json"
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
          expires_at: decodeJwtExpiry(refreshed.access_token)
        };
        await saveCredentials(creds);
      } catch {
        throw new AuthRequiredError();
      }
    }
    headers["Authorization"] = `Bearer ${creds.access_token}`;
    const doFetch = (token) => fetch(`${this.baseUrl}${path2}`, {
      method: "POST",
      headers: { ...headers, Authorization: `Bearer ${token}` },
      body: body != null ? JSON.stringify(body) : void 0,
      signal: AbortSignal.timeout(timeoutMs)
    });
    let res = await doFetch(creds.access_token);
    if (res.status === 401) {
      const latestCreds = await loadCredentials();
      if (latestCreds) {
        try {
          const refreshed = await refreshTokens(
            latestCreds.refresh_token,
            this.baseUrl
          );
          const newCreds = {
            ...latestCreds,
            access_token: refreshed.access_token,
            refresh_token: refreshed.refresh_token,
            expires_at: decodeJwtExpiry(refreshed.access_token)
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
};
var apiClient = new ApiClient();

// src/wizard/steps/00-company.ts
var INDUSTRY_CHOICES = [
  "SaaS / \uC18C\uD504\uD2B8\uC6E8\uC5B4",
  "\uC774\uCEE4\uBA38\uC2A4 / \uB9AC\uD14C\uC77C",
  "\uAE08\uC735 / \uD540\uD14C\uD06C",
  "\uD5EC\uC2A4\uCF00\uC5B4",
  "\uAD50\uC721 / \uC5D0\uB4C0\uD14C\uD06C",
  "\uBBF8\uB514\uC5B4 / \uCF58\uD150\uCE20",
  "\uC81C\uC870 / \uBB3C\uB958",
  "\uAE30\uD0C0"
];
var BUSINESS_TYPE_CHOICES = ["B2B", "B2C", "B2B2C", "\uB0B4\uBD80 \uB3C4\uAD6C"];
async function step00Company(state) {
  console.log(chalk.bold("\n\u{1F3E2} Step 0 \u2014 \uD68C\uC0AC & \uC194\uB8E8\uC158 \uC815\uBCF4\n"));
  const answers = await inquirer.prompt([
    {
      type: "input",
      name: "companyName",
      message: "\uD68C\uC0AC\uBA85:",
      default: state.company.companyName || void 0,
      validate: (v) => v.trim().length > 0 || "\uD68C\uC0AC\uBA85\uC744 \uC785\uB825\uD574 \uC8FC\uC138\uC694"
    },
    {
      type: "list",
      name: "industry",
      message: "\uC5C5\uC885:",
      choices: INDUSTRY_CHOICES,
      default: state.company.industry || INDUSTRY_CHOICES[0]
    },
    {
      type: "input",
      name: "techStack",
      message: "\uAE30\uC220 \uC2A4\uD0DD (\uC27C\uD45C \uAD6C\uBD84, \uC608: React, FastAPI, PostgreSQL):",
      default: state.company.techStack.join(", ") || void 0
    },
    {
      type: "input",
      name: "mainProduct",
      message: "\uC8FC\uC694 \uC81C\uD488/\uC11C\uBE44\uC2A4 \uC124\uBA85:",
      default: state.company.mainProduct || void 0
    },
    {
      type: "list",
      name: "businessType",
      message: "\uBE44\uC988\uB2C8\uC2A4 \uC720\uD615:",
      choices: BUSINESS_TYPE_CHOICES,
      default: state.company.businessType || BUSINESS_TYPE_CHOICES[0]
    },
    {
      type: "input",
      name: "solutionPrompt",
      message: "\uB9CC\uB4E4\uACE0 \uC2F6\uC740 AI \uC194\uB8E8\uC158\uC744 \uC124\uBA85\uD574 \uC8FC\uC138\uC694:",
      default: state.company.solutionPrompt || void 0,
      validate: (v) => v.trim().length > 10 || "\uC194\uB8E8\uC158 \uC124\uBA85\uC744 10\uC790 \uC774\uC0C1 \uC785\uB825\uD574 \uC8FC\uC138\uC694"
    },
    {
      type: "confirm",
      name: "enableAutoDecompose",
      message: "\uC194\uB8E8\uC158 \uC790\uB3D9 \uBD84\uD574(Auto Decompose) \uD65C\uC131\uD654:",
      default: state.company.enableAutoDecompose
    }
  ]);
  const techStack = answers.techStack.split(",").map((s) => s.trim()).filter(Boolean);
  const org = await apiClient.post("/api/v1/organizations/", {
    company_name: answers.companyName,
    industry: answers.industry,
    tech_stack: techStack,
    main_product: answers.mainProduct,
    business_type: answers.businessType
  });
  const session = await apiClient.post(
    "/api/v1/prototype-sessions/",
    {
      organization_id: org.id,
      solution_prompt: answers.solutionPrompt,
      tech_stack: techStack,
      industry: answers.industry
    }
  );
  return {
    ...state,
    organizationId: org.id,
    sessionId: session.id,
    currentStep: 1,
    company: {
      companyName: answers.companyName,
      industry: answers.industry,
      techStack,
      mainProduct: answers.mainProduct,
      businessType: answers.businessType,
      solutionPrompt: answers.solutionPrompt,
      enableAutoDecompose: answers.enableAutoDecompose
    }
  };
}

// src/wizard/steps/01-generation.ts
import chalk2 from "chalk";
import ora from "ora";
var POLL_INTERVAL_MS = 3e3;
var POLL_TIMEOUT_MS = 5 * 60 * 1e3;
async function step01Generation(state, options = {}) {
  const pollIntervalMs = options.pollIntervalMs ?? POLL_INTERVAL_MS;
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk2.bold("\n\u{1F916} Step 1 \u2014 \uD504\uB85C\uD1A0\uD0C0\uC785 \uC0DD\uC131\n"));
  const spinner = ora("\uD504\uB85C\uD1A0\uD0C0\uC785 \uC0DD\uC131 \uC694\uCCAD \uC911...").start();
  try {
    await apiClient.post(
      `/api/v1/prototype-sessions/${state.sessionId}/prototypes/generate`
    );
    spinner.text = "AI\uAC00 \uD504\uB85C\uD1A0\uD0C0\uC785\uC744 \uC0DD\uC131\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...";
    let done = false;
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (Date.now() < deadline) {
      const { status } = await apiClient.get(
        `/api/v1/prototype-sessions/${state.sessionId}/status`
      );
      if (status === "completed") {
        done = true;
        break;
      }
      if (status === "failed") {
        throw new Error("\uD504\uB85C\uD1A0\uD0C0\uC785 \uC0DD\uC131\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC8FC\uC138\uC694.");
      }
      await new Promise((r) => setTimeout(r, pollIntervalMs));
    }
    if (!done) {
      throw new Error("\uD504\uB85C\uD1A0\uD0C0\uC785 \uC0DD\uC131 \uC2DC\uAC04\uC774 \uCD08\uACFC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.");
    }
    const list = await apiClient.get(
      `/api/v1/prototype-sessions/${state.sessionId}/prototypes`
    );
    spinner.succeed("\uD504\uB85C\uD1A0\uD0C0\uC785 \uC0DD\uC131 \uC644\uB8CC!");
    const prototypes = list.items.map((p) => ({
      id: p.id,
      variantIndex: p.variant_index,
      title: p.title,
      description: p.description,
      isRecommended: p.is_recommended,
      pros: p.pros,
      cons: p.cons
    }));
    return {
      ...state,
      currentStep: 2,
      prototypes: {
        ...state.prototypes,
        prototypes
      }
    };
  } catch (err) {
    if (!spinner.isSpinning) throw err;
    spinner.fail("\uD504\uB85C\uD1A0\uD0C0\uC785 \uC0DD\uC131 \uC624\uB958");
    throw err;
  }
}

// src/wizard/steps/02-prototype-select.ts
import inquirer2 from "inquirer";
import chalk3 from "chalk";
async function step02PrototypeSelect(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk3.bold("\n\u{1F3A8} Step 2 \u2014 \uD504\uB85C\uD1A0\uD0C0\uC785 \uC120\uD0DD\n"));
  const { prototypes } = state.prototypes;
  if (prototypes.length === 0) {
    throw new Error("\uC120\uD0DD\uD560 \uD504\uB85C\uD1A0\uD0C0\uC785\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.");
  }
  const choices = prototypes.map((p) => ({
    name: `${p.isRecommended ? "\u2B50 " : "  "}${p.title}` + (p.description ? chalk3.dim(` \u2014 ${p.description.slice(0, 60)}`) : ""),
    value: p.id,
    short: p.title
  }));
  const { selectedId } = await inquirer2.prompt([
    {
      type: "list",
      name: "selectedId",
      message: "\uC0AC\uC6A9\uD560 \uD504\uB85C\uD1A0\uD0C0\uC785\uC744 \uC120\uD0DD\uD574 \uC8FC\uC138\uC694:",
      choices,
      default: prototypes.find((p) => p.isRecommended)?.id
    }
  ]);
  const selected = prototypes.find((p) => p.id === selectedId);
  console.log(chalk3.bold(`
\u2705 \uC120\uD0DD\uB428: ${selected.title}`));
  if (selected.pros.length > 0) {
    console.log(chalk3.green("  \uC7A5\uC810:"));
    selected.pros.forEach((p) => console.log(`  \u2022 ${p}`));
  }
  if (selected.cons.length > 0) {
    console.log(chalk3.yellow("  \uB2E8\uC810:"));
    selected.cons.forEach((c) => console.log(`  \u2022 ${c}`));
  }
  console.log();
  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    selected_prototype_id: selectedId,
    current_step: 3
  });
  return {
    ...state,
    currentStep: 3,
    prototypes: {
      ...state.prototypes,
      selectedPrototypeId: selectedId
    }
  };
}

// src/wizard/steps/03-pm-recommend.ts
import chalk4 from "chalk";
import ora2 from "ora";
async function step03PMRecommend(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk4.bold("\n\u{1F454} Step 3 \u2014 PM \uCD94\uCC9C\n"));
  const spinner = ora2("AI\uAC00 \uCD5C\uC801\uC758 PM\uC744 \uCD94\uCC9C\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...").start();
  try {
    const res = await apiClient.post(
      `/api/v1/prototype-sessions/${state.sessionId}/recommend-pms`
    );
    spinner.succeed(`${res.items.length}\uBA85\uC758 PM \uCD94\uCC9C \uC644\uB8CC!`);
    const recommendedPMs = res.items.map((p) => ({
      pmId: p.pm_id,
      name: p.name,
      slug: p.slug,
      title: p.title,
      domain: p.domain,
      matchScore: p.match_score,
      reasoning: p.reasoning
    }));
    console.log(chalk4.bold("\n\u{1F4CB} \uCD94\uCC9C PM \uBAA9\uB85D:\n"));
    recommendedPMs.forEach((pm, i) => {
      const score = Math.round(pm.matchScore * 100);
      console.log(
        `  ${chalk4.bold(String(i + 1))}. ${chalk4.cyan(pm.name)} ` + chalk4.dim(`(${pm.title ?? pm.domain ?? "PM"})`) + ` \u2014 \uB9E4\uCE6D ${chalk4.green(`${score}%`)}`
      );
      const preview = pm.reasoning.length > 80 ? `${pm.reasoning.slice(0, 80)}...` : pm.reasoning;
      console.log(`     ${chalk4.dim(preview)}`);
    });
    console.log();
    return {
      ...state,
      currentStep: 4,
      pm: {
        ...state.pm,
        recommendedPMs
      }
    };
  } catch (err) {
    spinner.fail("PM \uCD94\uCC9C \uC2E4\uD328");
    throw err;
  }
}

// src/wizard/steps/04-pm-select.ts
import inquirer3 from "inquirer";
import chalk5 from "chalk";
async function step04PMSelect(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk5.bold("\n\u270B Step 4 \u2014 PM \uC120\uD0DD\n"));
  const { recommendedPMs } = state.pm;
  if (recommendedPMs.length === 0) {
    throw new Error("\uCD94\uCC9C\uB41C PM\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. Step 3\uC744 \uB2E4\uC2DC \uC2E4\uD589\uD574 \uC8FC\uC138\uC694.");
  }
  const choices = recommendedPMs.map((pm) => {
    const score = Math.round(pm.matchScore * 100);
    const meta = pm.title ?? pm.domain ?? "";
    return {
      name: `${chalk5.cyan(pm.name)} ` + chalk5.dim(`[${score}% \uB9E4\uCE6D]`) + (meta ? ` \u2014 ${meta}` : ""),
      value: pm.pmId,
      short: pm.name
    };
  });
  const { selectedPmId } = await inquirer3.prompt([
    {
      type: "list",
      name: "selectedPmId",
      message: "\uD568\uAED8\uD560 PM\uC744 \uC120\uD0DD\uD574 \uC8FC\uC138\uC694:",
      choices
    }
  ]);
  const selected = recommendedPMs.find((p) => p.pmId === selectedPmId);
  if (!selected) throw new Error(`\uC120\uD0DD\uB41C PM\uC744 \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4: ${selectedPmId}`);
  console.log(chalk5.bold(`
\u2705 \uC120\uD0DD\uB428: ${selected.name}`));
  if (selected.title) console.log(chalk5.dim(`   ${selected.title}`));
  if (selected.domain) console.log(chalk5.dim(`   \uC804\uBB38 \uB3C4\uBA54\uC778: ${selected.domain}`));
  console.log(chalk5.dim(`   \uCD94\uCC9C \uC774\uC720: ${selected.reasoning}`));
  console.log();
  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    selected_pm_id: selectedPmId,
    current_step: 5
  });
  return {
    ...state,
    currentStep: 5,
    pm: {
      ...state.pm,
      selectedPmProfileId: selectedPmId
    }
  };
}

// src/wizard/steps/05-pm-composition.ts
import inquirer4 from "inquirer";
import chalk6 from "chalk";
function renderSection(emoji, title, items) {
  if (items.length === 0) return;
  const sorted = [...items].sort((a, b) => a.display_order - b.display_order);
  console.log(chalk6.bold(`  ${emoji} ${title} (${sorted.length}\uAC1C)`));
  for (const item of sorted) {
    const badge = item.is_required ? chalk6.red("[\uD544\uC218]") : chalk6.dim("[\uC120\uD0DD]");
    console.log(
      `    ${badge} ${chalk6.cyan(item.component_name)} ` + chalk6.dim(`(${item.component_slug})`)
    );
    const rawDesc = item.config["description"];
    const desc = typeof rawDesc === "string" ? rawDesc : void 0;
    if (desc) console.log(`         ${chalk6.dim(desc)}`);
  }
  console.log();
}
async function step05PMComposition(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  if (!state.pm.selectedPmProfileId) throw new Error("\uC120\uD0DD\uB41C PM\uC774 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk6.bold("\n\u{1F9E9} Step 5 \u2014 PM \uAD6C\uC131 \uD655\uC778\n"));
  const composition = await apiClient.get(
    `/api/v1/pm-profiles/${state.pm.selectedPmProfileId}/composition`
  );
  const selectedPM = state.pm.recommendedPMs.find(
    (p) => p.pmId === state.pm.selectedPmProfileId
  );
  console.log(
    chalk6.bold(`${selectedPM?.name ?? "\uC120\uD0DD\uB41C PM"}\uC758 \uAE30\uBCF8 \uAD6C\uC131 \uC2A4\uD0DD:
`)
  );
  renderSection("\u{1F916}", "\uC5D0\uC774\uC804\uD2B8", composition.agents);
  renderSection("\u{1F527}", "\uC2A4\uD0AC", composition.skills);
  renderSection("\u{1FA9D}", "\uD6C5", composition.hooks);
  renderSection("\u{1F310}", "MCP \uC11C\uBC84", composition.mcp_servers);
  renderSection("\u{1F50C}", "\uD50C\uB7EC\uADF8\uC778", composition.plugins);
  const { confirmed } = await inquirer4.prompt([
    {
      type: "confirm",
      name: "confirmed",
      message: "\uC774 \uAD6C\uC131\uC73C\uB85C \uACC4\uC18D\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
      default: true
    }
  ]);
  if (!confirmed) {
    console.log(
      chalk6.yellow(
        "\n\u2B05\uFE0F  \uCDE8\uC18C\uB428. \uC7AC\uC2DC\uB3C4\uD558\uB824\uBA74 `ce init --resume` \uC635\uC158\uC744 \uC0AC\uC6A9\uD558\uC138\uC694.\n"
      )
    );
    process.exit(0);
  }
  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    current_step: 6
  });
  return {
    ...state,
    currentStep: 6
  };
}

// src/wizard/steps/06-agents.ts
import inquirer5 from "inquirer";
import chalk7 from "chalk";

// src/api/catalog.ts
var CACHE_TTL_MS = 5 * 60 * 1e3;
var cache = /* @__PURE__ */ new Map();
function getCache(key) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expiresAt) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}
function setCache(key, data) {
  cache.set(key, { data, expiresAt: Date.now() + CACHE_TTL_MS });
}
async function fetchAgents() {
  const cached = getCache("agents");
  if (cached) return cached;
  const res = await apiClient.get(
    "/api/v1/catalog/agents"
  );
  setCache("agents", res.items);
  return res.items;
}
async function fetchSkills() {
  const cached = getCache("skills");
  if (cached) return cached;
  const res = await apiClient.get(
    "/api/v1/catalog/skills"
  );
  setCache("skills", res.items);
  return res.items;
}
async function fetchHooks() {
  const cached = getCache("hooks");
  if (cached) return cached;
  const res = await apiClient.get(
    "/api/v1/catalog/hooks"
  );
  setCache("hooks", res.items);
  return res.items;
}
async function fetchPlatforms() {
  const cached = getCache("platforms");
  if (cached) return cached;
  const res = await apiClient.get(
    "/api/v1/catalog/platforms"
  );
  setCache("platforms", res.items);
  return res.items;
}
async function fetchPipelines() {
  const cached = getCache("pipelines");
  if (cached) return cached;
  const res = await apiClient.get(
    "/api/v1/catalog/pipelines"
  );
  setCache("pipelines", res.items);
  return res.items;
}
async function fetchCatalog(category) {
  switch (category) {
    case "agents":
      return fetchAgents();
    case "skills":
      return fetchSkills();
    case "hooks":
      return fetchHooks();
    case "platforms":
      return fetchPlatforms();
    case "pipelines":
      return fetchPipelines();
    default: {
      const _exhaustive = category;
      throw new Error(`\uC54C \uC218 \uC5C6\uB294 \uCE74\uD0C8\uB85C\uADF8 \uCE74\uD14C\uACE0\uB9AC: ${_exhaustive}`);
    }
  }
}
function clearCatalogCache() {
  cache.clear();
}

// src/wizard/steps/06-agents.ts
function isRecommended(idOrSlug, recommended) {
  return recommended.includes(idOrSlug);
}
async function step06Agents(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk7.bold("\n\u{1F916} Step 6 \u2014 \uC5D0\uC774\uC804\uD2B8 & \uC2A4\uD0AC \uAD6C\uC131\n"));
  let recommended = {
    agents: [],
    skills: [],
    excluded_agents: [],
    reasoning: null
  };
  try {
    recommended = await apiClient.get(
      `/api/v1/prototype-sessions/${state.sessionId}/recommend-components`
    );
    if (recommended.reasoning) {
      console.log(
        chalk7.dim(
          `\u{1F4A1} \uCD94\uCC9C \uADFC\uAC70: ${recommended.reasoning.slice(0, 100)}${recommended.reasoning.length > 100 ? "..." : ""}
`
        )
      );
    }
  } catch {
  }
  const [catalogAgents, catalogSkills, catalogHooks] = await Promise.all([
    fetchAgents(),
    fetchSkills(),
    fetchHooks()
  ]);
  const eligibleAgents = catalogAgents.filter(
    (a) => !isRecommended(a.id, recommended.excluded_agents) && !isRecommended(a.slug, recommended.excluded_agents)
  );
  if (eligibleAgents.length === 0) {
    throw new Error("\uC5D0\uC774\uC804\uD2B8 \uCE74\uD0C8\uB85C\uADF8\uAC00 \uBE44\uC5B4 \uC788\uC2B5\uB2C8\uB2E4. \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC8FC\uC138\uC694.");
  }
  let selectedAgents = [];
  while (selectedAgents.length === 0) {
    const agentChoices = eligibleAgents.map((a) => ({
      name: `${chalk7.cyan(a.slug.padEnd(22))} ${a.label}`,
      value: a.id,
      checked: isRecommended(a.id, recommended.agents) || isRecommended(a.slug, recommended.agents)
    }));
    const answer = await inquirer5.prompt([
      {
        type: "checkbox",
        name: "agents",
        message: "\uC5D0\uC774\uC804\uD2B8\uB97C \uC120\uD0DD\uD574 \uC8FC\uC138\uC694 (\uCD5C\uC18C 1\uAC1C):",
        choices: agentChoices
      }
    ]);
    if (answer.agents.length === 0) {
      console.log(chalk7.red("  \u274C \uC5D0\uC774\uC804\uD2B8\uB97C \uCD5C\uC18C 1\uAC1C \uC120\uD0DD\uD574\uC57C \uD569\uB2C8\uB2E4.\n"));
    } else {
      selectedAgents = answer.agents;
    }
  }
  const ticketSourceSkills = catalogSkills.filter(
    (s) => s.category === "ticket_source"
  );
  const otherSkills = catalogSkills.filter(
    (s) => s.category !== "ticket_source"
  );
  const selectedSkills = [];
  if (ticketSourceSkills.length > 0) {
    console.log(chalk7.bold("\n\u{1F3AB} \uD2F0\uCF13 \uC18C\uC2A4 \uC120\uD0DD (\uD544\uC218 \u2014 1\uAC1C):"));
    const preSelected = ticketSourceSkills.find(
      (s) => isRecommended(s.id, recommended.skills) || isRecommended(s.slug, recommended.skills)
    );
    const { ticketSource } = await inquirer5.prompt([
      {
        type: "list",
        name: "ticketSource",
        message: "\uD2F0\uCF13 \uC18C\uC2A4\uB97C \uC120\uD0DD\uD574 \uC8FC\uC138\uC694:",
        choices: ticketSourceSkills.map((s) => ({
          name: `${chalk7.cyan(s.slug.padEnd(20))} ${s.label}`,
          value: s.id
        })),
        default: preSelected?.id ?? ticketSourceSkills[0]?.id
      }
    ]);
    selectedSkills.push(ticketSource);
  }
  if (otherSkills.length > 0) {
    console.log(chalk7.bold("\n\u{1F527} \uCD94\uAC00 \uC2A4\uD0AC \uC120\uD0DD (\uC120\uD0DD):"));
    const skillChoices = otherSkills.map((s) => ({
      name: `${chalk7.cyan(s.slug.padEnd(22))} ${s.label}`,
      value: s.id,
      checked: isRecommended(s.id, recommended.skills) || isRecommended(s.slug, recommended.skills)
    }));
    const { additionalSkills } = await inquirer5.prompt([
      {
        type: "checkbox",
        name: "additionalSkills",
        message: "\uCD94\uAC00 \uC2A4\uD0AC\uC744 \uC120\uD0DD\uD574 \uC8FC\uC138\uC694:",
        choices: skillChoices
      }
    ]);
    selectedSkills.push(...additionalSkills);
  }
  let selectedHooks = [];
  if (catalogHooks.length > 0) {
    const { hooks } = await inquirer5.prompt([
      {
        type: "checkbox",
        name: "hooks",
        message: "\uD6C5\uC744 \uC120\uD0DD\uD574 \uC8FC\uC138\uC694 (\uC120\uD0DD):",
        choices: catalogHooks.map((h) => ({
          name: `${chalk7.cyan(h.slug.padEnd(22))} ${h.label}`,
          value: h.id,
          checked: false
        }))
      }
    ]);
    selectedHooks = hooks;
  }
  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    current_step: 7
  });
  return {
    ...state,
    currentStep: 7,
    agents: {
      selectedAgents,
      selectedSkills,
      selectedHooks
    }
  };
}

// src/wizard/steps/07-platform.ts
import inquirer6 from "inquirer";
import chalk8 from "chalk";
async function step07Platform(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk8.bold("\n\u{1F5A5}\uFE0F  Step 7 \u2014 \uD50C\uB7AB\uD3FC \uC120\uD0DD\n"));
  const platforms = await fetchPlatforms();
  if (platforms.length === 0) {
    throw new Error("\uD50C\uB7AB\uD3FC \uCE74\uD0C8\uB85C\uADF8\uAC00 \uBE44\uC5B4 \uC788\uC2B5\uB2C8\uB2E4. \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uC2DC\uB3C4\uD574 \uC8FC\uC138\uC694.");
  }
  const { platformId } = await inquirer6.prompt([
    {
      type: "list",
      name: "platformId",
      message: "\uBC30\uD3EC \uD50C\uB7AB\uD3FC\uC744 \uC120\uD0DD\uD574 \uC8FC\uC138\uC694:",
      choices: platforms.map((p) => ({
        name: p.label,
        value: p.id
      }))
    }
  ]);
  const selected = platforms.find((p) => p.id === platformId);
  console.log(chalk8.bold(`
\u2705 \uC120\uD0DD\uB428: ${selected?.label ?? platformId}
`));
  return {
    ...state,
    currentStep: 8,
    platform: { platformId }
  };
}

// src/wizard/steps/08-os.ts
import inquirer7 from "inquirer";
import chalk9 from "chalk";
var WSL2_OS_ID = "wsl2";
async function step08Os(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk9.bold("\n\u{1F427} Step 8 \u2014 \uC2E4\uD589 \uD658\uACBD \uC120\uD0DD\n"));
  console.log(
    chalk9.dim(
      "\uD604\uC7AC \uC9C0\uC6D0\uD558\uB294 \uC2E4\uD589 \uD658\uACBD\uC740 WSL2(Windows Subsystem for Linux 2)\uC785\uB2C8\uB2E4.\nmacOS/Linux \uB124\uC774\uD2F0\uBE0C \uC9C0\uC6D0\uC740 \uCD94\uD6C4 \uCD94\uAC00\uB420 \uC608\uC815\uC785\uB2C8\uB2E4.\n"
    )
  );
  const { confirmed } = await inquirer7.prompt([
    {
      type: "confirm",
      name: "confirmed",
      message: "WSL2 \uD658\uACBD\uC73C\uB85C \uACC4\uC18D\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
      default: true
    }
  ]);
  if (!confirmed) {
    console.log(
      chalk9.yellow(
        "\n\u2B05\uFE0F  \uCDE8\uC18C\uB428. \uC7AC\uC2DC\uB3C4\uD558\uB824\uBA74 `ce init --resume` \uC635\uC158\uC744 \uC0AC\uC6A9\uD558\uC138\uC694.\n"
      )
    );
    process.exit(0);
  }
  return {
    ...state,
    currentStep: 9,
    os: { osId: WSL2_OS_ID }
  };
}

// src/wizard/steps/09-env.ts
import inquirer8 from "inquirer";
import chalk10 from "chalk";
import ora3 from "ora";
async function validateLinear(apiKey, teamId) {
  return apiClient.post("/api/v1/integrations/validate/linear", {
    api_key: apiKey,
    team_id: teamId
  });
}
async function validateNotion(apiKey, databaseId) {
  return apiClient.post("/api/v1/integrations/validate/notion", {
    api_key: apiKey,
    database_id: databaseId
  });
}
var SKIP_LABEL = "\uB098\uC911\uC5D0 \uC785\uB825 (ZIP \uB2E4\uC6B4\uB85C\uB4DC \uC804\uAE4C\uC9C0 \uC785\uB825\uD558\uBA74 \uB429\uB2C8\uB2E4)";
async function step09Env(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk10.bold("\n\u2699\uFE0F  Step 9 \u2014 \uD658\uACBD \uC124\uC815\n"));
  const { authMethod } = await inquirer8.prompt([
    {
      type: "list",
      name: "authMethod",
      message: "Claude \uC778\uC99D \uBC29\uC2DD\uC744 \uC120\uD0DD\uD574 \uC8FC\uC138\uC694:",
      choices: [
        {
          name: `${chalk10.cyan("API Key")}            Anthropic API \uD0A4\uB97C \uC9C1\uC811 \uC0AC\uC6A9`,
          value: "api_key"
        },
        {
          name: `${chalk10.cyan("OAuth (\uBE0C\uB77C\uC6B0\uC800)")}   \uBE0C\uB77C\uC6B0\uC800\uB85C Claude.ai \uB85C\uADF8\uC778 (Pro/Max \uACC4\uC815)`,
          value: "oauth_browser"
        },
        {
          name: `${chalk10.cyan("OAuth (Setup Token)")} \uC11C\uBC84 \uD658\uACBD\uC6A9 Claude OAuth \uD1A0\uD070`,
          value: "oauth_setup_token"
        }
      ]
    }
  ]);
  const envVars = {};
  const deferredEnvVars = [];
  if (authMethod === "api_key") {
    const { apiKey } = await inquirer8.prompt([
      {
        type: "password",
        name: "apiKey",
        message: `Anthropic API \uD0A4 (sk-ant-...) ${chalk10.dim("[Enter\uB85C \uAC74\uB108\uB6F0\uAE30]")}:`,
        validate: (v) => {
          if (v.trim() === "") return true;
          return v.trim().startsWith("sk-") ? true : "\uC62C\uBC14\uB978 API \uD0A4 \uD615\uC2DD\uC774 \uC544\uB2D9\uB2C8\uB2E4 (sk-\uB85C \uC2DC\uC791\uD574\uC57C \uD569\uB2C8\uB2E4)";
        }
      }
    ]);
    if (apiKey.trim()) {
      envVars["ANTHROPIC_API_KEY"] = apiKey.trim();
    } else {
      deferredEnvVars.push("ANTHROPIC_API_KEY");
      console.log(chalk10.dim("  \u2192 ANTHROPIC_API_KEY: ZIP \uB2E4\uC6B4\uB85C\uB4DC \uC804\uC5D0 \uC785\uB825\uD569\uB2C8\uB2E4.\n"));
    }
  } else if (authMethod === "oauth_setup_token") {
    const { setupToken } = await inquirer8.prompt([
      {
        type: "password",
        name: "setupToken",
        message: `Claude OAuth Setup Token ${chalk10.dim("[Enter\uB85C \uAC74\uB108\uB6F0\uAE30]")}:`
      }
    ]);
    if (setupToken.trim()) {
      envVars["CLAUDE_OAUTH_SETUP_TOKEN"] = setupToken.trim();
    } else {
      deferredEnvVars.push("CLAUDE_OAUTH_SETUP_TOKEN");
      console.log(chalk10.dim("  \u2192 CLAUDE_OAUTH_SETUP_TOKEN: ZIP \uB2E4\uC6B4\uB85C\uB4DC \uC804\uC5D0 \uC785\uB825\uD569\uB2C8\uB2E4.\n"));
    }
  }
  const allSkills = await fetchSkills();
  const selectedSkillObjects = allSkills.filter(
    (s) => state.agents.selectedSkills.includes(s.id)
  );
  const selectedSlugs = selectedSkillObjects.map((s) => s.slug);
  const LINEAR_SLUGS = /* @__PURE__ */ new Set(["linear-reader", "linear-writer"]);
  const NOTION_SLUGS = /* @__PURE__ */ new Set(["notion-reader", "notion-writer"]);
  const hasLinear = selectedSlugs.some((slug) => LINEAR_SLUGS.has(slug));
  const hasNotion = selectedSlugs.some((slug) => NOTION_SLUGS.has(slug));
  const MAX_VALIDATION_ATTEMPTS = 3;
  if (hasLinear) {
    console.log(chalk10.bold("\n\u{1F4CB} Linear \uD1B5\uD569 \uC124\uC815:"));
    const { linearSetupChoice } = await inquirer8.prompt([
      {
        type: "list",
        name: "linearSetupChoice",
        message: "Linear API \uD0A4\uB97C \uC5B8\uC81C \uC785\uB825\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
        choices: [
          { name: "\uC9C0\uAE08 \uC124\uC815", value: "now" },
          { name: SKIP_LABEL, value: "later" }
        ]
      }
    ]);
    if (linearSetupChoice === "later") {
      deferredEnvVars.push("LINEAR_API_KEY", "LINEAR_TEAM_ID");
      console.log(chalk10.dim("  \u2192 LINEAR_API_KEY, LINEAR_TEAM_ID: ZIP \uB2E4\uC6B4\uB85C\uB4DC \uC804\uC5D0 \uC785\uB825\uD569\uB2C8\uB2E4.\n"));
    } else {
      let linearValid = false;
      let linearAttempts = 0;
      while (!linearValid) {
        if (linearAttempts >= MAX_VALIDATION_ATTEMPTS) {
          console.log(chalk10.yellow(`
\u26A0\uFE0F  Linear \uAC80\uC99D ${MAX_VALIDATION_ATTEMPTS}\uD68C \uC2E4\uD328. \uB098\uC911\uC5D0 \uC785\uB825\uD558\uB3C4\uB85D \uC720\uC608\uD569\uB2C8\uB2E4.
`));
          deferredEnvVars.push("LINEAR_API_KEY", "LINEAR_TEAM_ID");
          break;
        }
        linearAttempts++;
        const { linearApiKey, linearTeamId } = await inquirer8.prompt([
          {
            type: "password",
            name: "linearApiKey",
            message: "Linear API \uD0A4 (lin_api_...):",
            validate: (v) => v.trim().startsWith("lin_api_") ? true : "Linear API \uD0A4\uB294 lin_api_\uB85C \uC2DC\uC791\uD574\uC57C \uD569\uB2C8\uB2E4"
          },
          {
            type: "input",
            name: "linearTeamId",
            message: "Linear \uD300 ID (UUID):",
            validate: (v) => v.trim().length > 0 ? true : "\uD300 ID\uB97C \uC785\uB825\uD574 \uC8FC\uC138\uC694"
          }
        ]);
        const spinner = ora3("Linear API \uD0A4 \uAC80\uC99D \uC911...").start();
        try {
          const result = await validateLinear(linearApiKey.trim(), linearTeamId.trim());
          if (result.valid) {
            spinner.succeed("Linear \uC5F0\uACB0 \uD655\uC778\uB428");
            envVars["LINEAR_API_KEY"] = linearApiKey.trim();
            envVars["LINEAR_TEAM_ID"] = linearTeamId.trim();
            linearValid = true;
          } else {
            spinner.fail(`Linear \uAC80\uC99D \uC2E4\uD328: ${result.message}`);
            console.log(chalk10.yellow(`  \uB2E4\uC2DC \uC785\uB825\uD574 \uC8FC\uC138\uC694. (${linearAttempts}/${MAX_VALIDATION_ATTEMPTS})
`));
          }
        } catch {
          spinner.fail("Linear API \uAC80\uC99D \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.");
          console.log(chalk10.yellow(`  \uB2E4\uC2DC \uC785\uB825\uD574 \uC8FC\uC138\uC694. (${linearAttempts}/${MAX_VALIDATION_ATTEMPTS})
`));
        }
      }
    }
  }
  if (hasNotion) {
    console.log(chalk10.bold("\n\u{1F4D3} Notion \uD1B5\uD569 \uC124\uC815:"));
    const { notionSetupChoice } = await inquirer8.prompt([
      {
        type: "list",
        name: "notionSetupChoice",
        message: "Notion API \uD0A4\uB97C \uC5B8\uC81C \uC785\uB825\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
        choices: [
          { name: "\uC9C0\uAE08 \uC124\uC815", value: "now" },
          { name: SKIP_LABEL, value: "later" }
        ]
      }
    ]);
    if (notionSetupChoice === "later") {
      deferredEnvVars.push("NOTION_API_KEY", "NOTION_DATABASE_ID");
      console.log(chalk10.dim("  \u2192 NOTION_API_KEY, NOTION_DATABASE_ID: ZIP \uB2E4\uC6B4\uB85C\uB4DC \uC804\uC5D0 \uC785\uB825\uD569\uB2C8\uB2E4.\n"));
    } else {
      let notionValid = false;
      let notionAttempts = 0;
      while (!notionValid) {
        if (notionAttempts >= MAX_VALIDATION_ATTEMPTS) {
          console.log(chalk10.yellow(`
\u26A0\uFE0F  Notion \uAC80\uC99D ${MAX_VALIDATION_ATTEMPTS}\uD68C \uC2E4\uD328. \uB098\uC911\uC5D0 \uC785\uB825\uD558\uB3C4\uB85D \uC720\uC608\uD569\uB2C8\uB2E4.
`));
          deferredEnvVars.push("NOTION_API_KEY", "NOTION_DATABASE_ID");
          break;
        }
        notionAttempts++;
        const { notionApiKey, notionDatabaseId } = await inquirer8.prompt([
          {
            type: "password",
            name: "notionApiKey",
            message: "Notion API \uD0A4 (secret_...):",
            validate: (v) => v.trim().startsWith("secret_") ? true : "Notion API \uD0A4\uB294 secret_\uB85C \uC2DC\uC791\uD574\uC57C \uD569\uB2C8\uB2E4"
          },
          {
            type: "input",
            name: "notionDatabaseId",
            message: "Notion \uB370\uC774\uD130\uBCA0\uC774\uC2A4 ID (UUID):",
            validate: (v) => v.trim().length > 0 ? true : "\uB370\uC774\uD130\uBCA0\uC774\uC2A4 ID\uB97C \uC785\uB825\uD574 \uC8FC\uC138\uC694"
          }
        ]);
        const spinner = ora3("Notion API \uD0A4 \uAC80\uC99D \uC911...").start();
        try {
          const result = await validateNotion(notionApiKey.trim(), notionDatabaseId.trim());
          if (result.valid) {
            spinner.succeed("Notion \uC5F0\uACB0 \uD655\uC778\uB428");
            envVars["NOTION_API_KEY"] = notionApiKey.trim();
            envVars["NOTION_DATABASE_ID"] = notionDatabaseId.trim();
            notionValid = true;
          } else {
            spinner.fail(`Notion \uAC80\uC99D \uC2E4\uD328: ${result.message}`);
            console.log(chalk10.yellow(`  \uB2E4\uC2DC \uC785\uB825\uD574 \uC8FC\uC138\uC694. (${notionAttempts}/${MAX_VALIDATION_ATTEMPTS})
`));
          }
        } catch {
          spinner.fail("Notion API \uAC80\uC99D \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.");
          console.log(chalk10.yellow(`  \uB2E4\uC2DC \uC785\uB825\uD574 \uC8FC\uC138\uC694. (${notionAttempts}/${MAX_VALIDATION_ATTEMPTS})
`));
        }
      }
    }
  }
  for (const skill of selectedSkillObjects) {
    const requiredVars = (skill.env_vars ?? []).filter(
      (ev) => ev.required && !envVars[ev.name] && !deferredEnvVars.includes(ev.name)
    );
    for (const ev of requiredVars) {
      const desc = ev.description ? chalk10.dim(` (${ev.description})`) : "";
      const { value } = await inquirer8.prompt([
        {
          type: "password",
          name: "value",
          message: `${ev.name}${desc} ${chalk10.dim("[Enter\uB85C \uAC74\uB108\uB6F0\uAE30]")}:`
        }
      ]);
      if (value.trim()) {
        envVars[ev.name] = value.trim();
      } else {
        deferredEnvVars.push(ev.name);
        console.log(chalk10.dim(`  \u2192 ${ev.name}: ZIP \uB2E4\uC6B4\uB85C\uB4DC \uC804\uC5D0 \uC785\uB825\uD569\uB2C8\uB2E4.
`));
      }
    }
  }
  const deferredCount = deferredEnvVars.length;
  if (deferredCount > 0) {
    console.log(
      chalk10.dim(
        `
\u2705 \uD658\uACBD \uC124\uC815 \uC644\uB8CC (${Object.keys(envVars).length}\uAC1C \uC124\uC815\uB428, ${deferredCount}\uAC1C \uB098\uC911\uC5D0 \uC785\uB825 \uC608\uC815)
`
      )
    );
  } else {
    console.log(chalk10.dim(`
\u2705 \uD658\uACBD \uC124\uC815 \uC644\uB8CC (${Object.keys(envVars).length}\uAC1C \uBCC0\uC218 \uC124\uC815\uB428)
`));
  }
  return {
    ...state,
    currentStep: 10,
    env: { authMethod, envVars, deferredEnvVars: deferredCount > 0 ? deferredEnvVars : void 0 }
  };
}

// src/wizard/steps/10-roi.ts
import inquirer9 from "inquirer";
import chalk11 from "chalk";
import ora4 from "ora";
function formatKRW(amount) {
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency: "KRW",
    maximumFractionDigits: 0
  }).format(amount);
}
async function step10Roi(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk11.bold("\n\u{1F4CA} Step 10 \u2014 ROI \uBD84\uC11D\n"));
  const { complexity } = await inquirer9.prompt([
    {
      type: "list",
      name: "complexity",
      message: "\uD504\uB85C\uC81D\uD2B8 \uBCF5\uC7A1\uB3C4\uB97C \uC120\uD0DD\uD574 \uC8FC\uC138\uC694:",
      choices: [
        { name: "\uB0AE\uC74C (Low)   \u2014 \uB2E8\uC21C \uBC18\uBCF5 \uC5C5\uBB34 \uC790\uB3D9\uD654", value: "low" },
        { name: "\uC911\uAC04 (Medium) \u2014 \uBCF5\uD569 \uC6CC\uD06C\uD50C\uB85C \uC790\uB3D9\uD654", value: "medium" },
        { name: "\uB192\uC74C (High)  \u2014 \uB300\uADDC\uBAA8 \uBA40\uD2F0 \uC5D0\uC774\uC804\uD2B8 \uC2DC\uC2A4\uD15C", value: "high" }
      ],
      default: "medium"
    }
  ]);
  const selectedPrototype = state.prototypes.prototypes.find(
    (p) => p.id === state.prototypes.selectedPrototypeId
  );
  if (!selectedPrototype) {
    throw new Error(
      "\uC120\uD0DD\uB41C \uD504\uB85C\uD1A0\uD0C0\uC785\uC744 \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. `ce init --resume` \uB610\uB294 \uCC98\uC74C\uBD80\uD130 \uB2E4\uC2DC \uC2DC\uC791\uD574 \uC8FC\uC138\uC694."
    );
  }
  const solutionType = selectedPrototype.title;
  const spinner = ora4("ROI\uB97C \uACC4\uC0B0\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...").start();
  let roi;
  try {
    roi = await apiClient.post("/api/v1/roi/calculate", {
      solution_type: solutionType,
      complexity,
      selected_agents_count: state.agents.selectedAgents.length,
      selected_skills_count: state.agents.selectedSkills.length,
      selected_hooks_count: state.agents.selectedHooks.length,
      platform_id: state.platform.platformId
    });
    spinner.succeed("ROI \uACC4\uC0B0 \uC644\uB8CC!");
  } catch (err) {
    spinner.fail("ROI \uACC4\uC0B0 \uC2E4\uD328");
    throw err;
  }
  const savingsPct = Math.round(roi.savings_ratio * 100);
  console.log();
  console.log(
    chalk11.bold("  ROI \uBD84\uC11D \uACB0\uACFC") + chalk11.dim(` (\uACF5\uC2DD \uBC84\uC804: ${roi.formula_version})`)
  );
  console.log("  " + "\u2500".repeat(50));
  console.log(
    `  ${chalk11.dim("\uAE30\uC874 \uAC1C\uBC1C \uBE44\uC6A9:")}  ${chalk11.white(formatKRW(roi.baseline_cost))} ` + chalk11.dim(`(${roi.baseline_days}\uC77C)`)
  );
  console.log(
    `  ${chalk11.dim("ClickEye \uBE44\uC6A9:")}   ${chalk11.cyan(formatKRW(roi.clickeye_cost))} ` + chalk11.dim(`(${roi.clickeye_days}\uC77C)`)
  );
  console.log(
    `  ${chalk11.dim("\uC808\uAC10\uC561:")}           ${chalk11.green(formatKRW(roi.savings))} ` + chalk11.bold.green(`(${savingsPct}% \uC808\uAC10)`)
  );
  if (roi.breakdown.length > 0) {
    console.log();
    console.log(chalk11.bold("  \uC5ED\uD560\uBCC4 \uACF5\uC218:"));
    for (const item of roi.breakdown) {
      console.log(
        `    ${chalk11.dim(item.label.padEnd(20))} ${String(item.days).padStart(5)}\uC77C  ` + chalk11.dim(formatKRW(item.subtotal))
      );
    }
  }
  console.log();
  const { confirmed } = await inquirer9.prompt([
    {
      type: "confirm",
      name: "confirmed",
      message: "\uC774 ROI \uBD84\uC11D\uC73C\uB85C \uACC4\uC18D\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
      default: true
    }
  ]);
  if (!confirmed) {
    console.log(
      chalk11.yellow(
        "\n\u2B05\uFE0F  \uCDE8\uC18C\uB428. \uC7AC\uC2DC\uB3C4\uD558\uB824\uBA74 `ce init --resume` \uC635\uC158\uC744 \uC0AC\uC6A9\uD558\uC138\uC694.\n"
      )
    );
    process.exit(0);
  }
  return {
    ...state,
    currentStep: 11,
    roi: { result: roi }
  };
}

// src/wizard/steps/11-confirm.ts
import inquirer10 from "inquirer";
import chalk12 from "chalk";
import ora5 from "ora";

// src/api/download.ts
import { unlink as unlink3, mkdir as mkdir3, readdir as readdir2, writeFile as writeFile3 } from "fs/promises";
import { join as join3, resolve } from "path";
import { execFile } from "child_process";
import { promisify } from "util";
import { tmpdir } from "os";
import { randomUUID } from "crypto";
var execFileAsync = promisify(execFile);
var ZIP_TIMEOUT_MS = 12e4;
async function downloadAndExtract(projectId, envVars, projectName, destDir = process.cwd(), force = false) {
  try {
    await execFileAsync("unzip", ["--version"]);
  } catch {
    throw new Error(
      "`unzip`\uC774 \uC124\uCE58\uB418\uC5B4 \uC788\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. `sudo apt install unzip`\uC744 \uC2E4\uD589\uD574 \uC8FC\uC138\uC694."
    );
  }
  const safeName = projectName.replace(/[^a-zA-Z0-9가-힣._-]/g, "_");
  if (!safeName || /^\.+$/.test(safeName)) {
    throw new Error("\uC720\uD6A8\uD558\uC9C0 \uC54A\uC740 \uD504\uB85C\uC81D\uD2B8 \uC774\uB984\uC785\uB2C8\uB2E4.");
  }
  const projectDir = resolve(destDir, safeName);
  if (!force) {
    const dirFiles = await readdir2(projectDir).catch(() => []);
    if (dirFiles.length > 0) {
      throw new Error(
        `\uB300\uC0C1 \uB514\uB809\uD1A0\uB9AC\uAC00 \uBE44\uC5B4 \uC788\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4: ${projectDir}
  \`ce redownload <projectId>\`\uB97C \uC0AC\uC6A9\uD558\uBA74 \uB36E\uC5B4\uC4F8 \uC218 \uC788\uC2B5\uB2C8\uB2E4.`
      );
    }
  }
  const response = await apiClient.postRaw(
    `/api/v1/projects/${projectId}/redownload`,
    { env_vars: envVars },
    ZIP_TIMEOUT_MS
  );
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`ZIP \uB2E4\uC6B4\uB85C\uB4DC \uC2E4\uD328 (${response.status}): ${text}`);
  }
  const tmpZip = join3(tmpdir(), `ce-project-${randomUUID()}.zip`);
  const buffer = await response.arrayBuffer();
  await writeFile3(tmpZip, Buffer.from(buffer));
  await mkdir3(projectDir, { recursive: true });
  try {
    const flags = force ? ["-o", "-q", tmpZip, "-d", projectDir] : ["-q", tmpZip, "-d", projectDir];
    await execFileAsync("unzip", flags);
  } finally {
    await unlink3(tmpZip).catch(() => void 0);
  }
  return projectDir;
}

// src/wizard/steps/11-confirm.ts
async function step11Confirm(state) {
  if (!state.sessionId) throw new Error("\uC138\uC158 ID\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  console.log(chalk12.bold("\n\u2705 Step 11 \u2014 \uCD5C\uC885 \uD655\uC778\n"));
  const selectedPM = state.pm.recommendedPMs.find(
    (p) => p.pmId === state.pm.selectedPmProfileId
  );
  const selectedProto = state.prototypes.prototypes.find(
    (p) => p.id === state.prototypes.selectedPrototypeId
  );
  console.log(chalk12.bold("  \u{1F4CB} \uC124\uC815 \uC694\uC57D:"));
  console.log(`     \uD68C\uC0AC\uBA85:       ${chalk12.cyan(state.company.companyName)}`);
  console.log(`     \uD504\uB85C\uD1A0\uD0C0\uC785:   ${chalk12.cyan(selectedProto?.title ?? state.prototypes.selectedPrototypeId ?? "-")}`);
  console.log(`     PM:            ${chalk12.cyan(selectedPM?.name ?? state.pm.selectedPmProfileId ?? "-")}`);
  console.log(`     \uC5D0\uC774\uC804\uD2B8:     ${chalk12.cyan(String(state.agents.selectedAgents.length))}\uAC1C`);
  console.log(`     \uC2A4\uD0AC:         ${chalk12.cyan(String(state.agents.selectedSkills.length))}\uAC1C`);
  console.log(`     \uD6C5:           ${chalk12.cyan(String(state.agents.selectedHooks.length))}\uAC1C`);
  console.log(`     \uD50C\uB7AB\uD3FC:       ${chalk12.cyan(state.platform.platformId ?? "-")}`);
  console.log(`     \uC778\uC99D\uBC29\uC2DD:     ${chalk12.cyan(state.env.authMethod ?? "-")}`);
  console.log();
  const defaultName = state.company.companyName ? `${state.company.companyName.replace(/\s+/g, "-").toLowerCase()}-solution` : "clickeye-solution";
  const { projectName } = await inquirer10.prompt([
    {
      type: "input",
      name: "projectName",
      message: "\uD504\uB85C\uC81D\uD2B8 \uC774\uB984:",
      default: defaultName,
      validate: (v) => v.trim().length > 0 ? true : "\uD504\uB85C\uC81D\uD2B8 \uC774\uB984\uC744 \uC785\uB825\uD574 \uC8FC\uC138\uC694"
    }
  ]);
  const { confirmed } = await inquirer10.prompt([
    {
      type: "confirm",
      name: "confirmed",
      message: "\uC774 \uC124\uC815\uC73C\uB85C \uD504\uB85C\uC81D\uD2B8\uB97C \uC0DD\uC131\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
      default: true
    }
  ]);
  if (!confirmed) {
    console.log(
      chalk12.yellow(
        "\n\u2B05\uFE0F  \uCDE8\uC18C\uB428. \uC7AC\uC2DC\uB3C4\uD558\uB824\uBA74 `ce init --resume` \uC635\uC158\uC744 \uC0AC\uC6A9\uD558\uC138\uC694.\n"
      )
    );
    process.exit(0);
  }
  const deferred = state.env.deferredEnvVars ?? [];
  const finalEnvVars = { ...state.env.envVars };
  if (deferred.length > 0) {
    console.log(
      chalk12.yellow(
        "\n\u26A0\uFE0F  \uB2E4\uC74C \uD658\uACBD \uBCC0\uC218\uAC00 \uC544\uC9C1 \uC785\uB825\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4.\n   \uC9C0\uAE08 \uC785\uB825\uD558\uAC70\uB098 Enter\uB85C \uAC74\uB108\uB6F8 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\n"
      )
    );
    for (const varName of deferred) {
      const hasExisting = !!finalEnvVars[varName];
      const hint = hasExisting ? chalk12.dim(" [Enter\uB85C \uAE30\uC874 \uAC12 \uC720\uC9C0]") : "";
      const { value } = await inquirer10.prompt([
        {
          type: "password",
          name: "value",
          message: `${varName}${hint}:`
        }
      ]);
      if (value.trim()) {
        finalEnvVars[varName] = value.trim();
      }
    }
    console.log();
  }
  let missingVars = deferred.filter((v) => !finalEnvVars[v]);
  while (missingVars.length > 0) {
    console.log(
      chalk12.red(
        "\n\u{1F6AB} ZIP\uC744 \uB2E4\uC6B4\uB85C\uB4DC\uD558\uB824\uBA74 \uB2E4\uC74C \uD658\uACBD \uBCC0\uC218\uB97C \uBC18\uB4DC\uC2DC \uC785\uB825\uD574\uC57C \uD569\uB2C8\uB2E4:\n" + missingVars.map((v) => `   \u2022 ${v}`).join("\n")
      )
    );
    const { action } = await inquirer10.prompt([
      {
        type: "list",
        name: "action",
        message: "\uC5B4\uB5BB\uAC8C \uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
        choices: [
          { name: "\uC9C0\uAE08 \uC785\uB825\uD558\uAE30", value: "enter" },
          { name: "\uCDE8\uC18C (\uC138\uC158 \uC800\uC7A5 \uD6C4 \uB098\uC911\uC5D0 \uC7AC\uAC1C)", value: "cancel" }
        ]
      }
    ]);
    if (action === "cancel") {
      await saveSession({ ...state, env: { ...state.env, envVars: finalEnvVars } });
      console.log(
        chalk12.yellow(`
\u23F8  \uC138\uC158\uC774 \uC800\uC7A5\uB429\uB2C8\uB2E4. \uC7AC\uAC1C: ce init --resume ${state.sessionId}
`)
      );
      process.exit(0);
    }
    for (const varName of missingVars) {
      const { value } = await inquirer10.prompt([
        {
          type: "password",
          name: "value",
          message: `${varName}:`,
          validate: (v) => v.trim().length > 0 ? true : "\uAC12\uC744 \uC785\uB825\uD574\uC57C \uD569\uB2C8\uB2E4"
        }
      ]);
      finalEnvVars[varName] = value.trim();
    }
    missingVars = deferred.filter((v) => !finalEnvVars[v]);
  }
  const spinner = ora5("\uD504\uB85C\uC81D\uD2B8\uB97C \uC0DD\uC131\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...").start();
  let finalizeResult;
  try {
    finalizeResult = await apiClient.post(
      `/api/v1/prototype-sessions/${state.sessionId}/finalize`,
      {
        project_name: projectName.trim(),
        linear_api_key: finalEnvVars["LINEAR_API_KEY"] ?? null,
        linear_team_id: finalEnvVars["LINEAR_TEAM_ID"] ?? null,
        notion_api_key: finalEnvVars["NOTION_API_KEY"] ?? null,
        notion_database_id: finalEnvVars["NOTION_DATABASE_ID"] ?? null,
        hook_ids: state.agents.selectedHooks
      }
    );
    spinner.succeed(`\uD504\uB85C\uC81D\uD2B8 \uC0DD\uC131 \uC644\uB8CC: ${finalizeResult.project_name}`);
  } catch (err) {
    spinner.fail("\uD504\uB85C\uC81D\uD2B8 \uC0DD\uC131 \uC2E4\uD328");
    throw err;
  }
  const downloadSpinner = ora5("ZIP\uC744 \uB2E4\uC6B4\uB85C\uB4DC\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...").start();
  let projectDir;
  try {
    projectDir = await downloadAndExtract(
      finalizeResult.project_id,
      finalEnvVars,
      finalizeResult.project_name
    );
    downloadSpinner.succeed(`\uC555\uCD95 \uD574\uC81C \uC644\uB8CC: ${projectDir}`);
  } catch (err) {
    downloadSpinner.fail("ZIP \uB2E4\uC6B4\uB85C\uB4DC \uB610\uB294 \uC555\uCD95 \uD574\uC81C \uC2E4\uD328");
    throw err;
  }
  console.log();
  console.log(chalk12.bold.green("\u{1F389} ClickEye \uC194\uB8E8\uC158\uC774 \uC900\uBE44\uB418\uC5C8\uC2B5\uB2C8\uB2E4!\n"));
  console.log(`   \uD504\uB85C\uC81D\uD2B8 \uC704\uCE58: ${chalk12.cyan(projectDir)}`);
  if (finalizeResult.initial_task_url) {
    console.log(`   Linear \uC774\uC288:   ${chalk12.dim(finalizeResult.initial_task_url)}`);
  }
  console.log();
  console.log(chalk12.dim("  \uB2E4\uC74C \uB2E8\uACC4:"));
  console.log(chalk12.dim(`  1. cd ${projectDir}`));
  console.log(chalk12.dim("  2. cat README.md  (\uB610\uB294 cat .claude/README.md)"));
  console.log(chalk12.dim("  3. bash start.sh  (\uD658\uACBD \uC124\uC815 \uD6C4 \uC2E4\uD589)"));
  console.log();
  if (state.sessionId) {
    await deleteSession(state.sessionId).catch(() => void 0);
  }
  return {
    ...state,
    currentStep: 12
  };
}

// src/commands/init.ts
var STEP_RUNNERS = [
  step00Company,
  // 0
  step01Generation,
  // 1
  step02PrototypeSelect,
  // 2
  step03PMRecommend,
  // 3
  step04PMSelect,
  // 4
  step05PMComposition,
  // 5
  step06Agents,
  // 6
  step07Platform,
  // 7
  step08Os,
  // 8
  step09Env,
  // 9
  step10Roi,
  // 10
  step11Confirm
  // 11
];
async function initCommand(flags) {
  let state;
  if (flags.resume) {
    let loaded;
    try {
      loaded = await loadSession(flags.resume);
    } catch (err) {
      console.error(chalk13.red(`
\u274C ${String(err)}
`));
      process.exit(1);
    }
    if (!loaded) {
      console.error(
        chalk13.red(`
\u274C \uC138\uC158 '${flags.resume}'\uC744 \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.
`)
      );
      process.exit(1);
    }
    console.log(
      chalk13.cyan(
        `
\u{1F504} \uC138\uC158 \uC7AC\uAC1C: Step ${loaded.currentStep}\uBD80\uD130 \uC2DC\uC791\uD569\uB2C8\uB2E4.
`
      )
    );
    state = loaded;
  } else {
    const sessions = await listSessions();
    if (sessions.length > 0) {
      const choices = [
        ...sessions.map((s) => {
          const name = s.companyName ?? "(\uD68C\uC0AC\uBA85 \uBBF8\uC785\uB825)";
          const date = s.savedAt.toLocaleString("ko-KR", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit"
          });
          return {
            name: `[Step ${s.currentStep}/${STEP_RUNNERS.length}] ${chalk13.cyan(name)} \u2014 ${chalk13.dim(date)}`,
            value: s.sessionId
          };
        }),
        { name: chalk13.bold("\uC0C8\uB85C \uC2DC\uC791"), value: null }
      ];
      const { sessionChoice } = await inquirer11.prompt([
        {
          type: "list",
          name: "sessionChoice",
          message: "\u{1F4BE} \uC800\uC7A5\uB41C \uC9C4\uD589 \uC911 \uC138\uC158\uC774 \uC788\uC2B5\uB2C8\uB2E4. \uC5B4\uB5BB\uAC8C \uD560\uAE4C\uC694?",
          choices
        }
      ]);
      if (sessionChoice) {
        let loaded;
        try {
          loaded = await loadSession(sessionChoice);
        } catch (err) {
          console.error(chalk13.red(`
\u274C ${String(err)}
`));
          process.exit(1);
        }
        if (loaded) {
          console.log(chalk13.cyan(`
\u{1F504} \uC138\uC158 \uC7AC\uAC1C: Step ${loaded.currentStep}\uBD80\uD130 \uC2DC\uC791\uD569\uB2C8\uB2E4.
`));
          state = loaded;
        } else {
          console.log(chalk13.yellow("\n\u26A0\uFE0F  \uC138\uC158\uC744 \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uC0C8\uB85C \uC2DC\uC791\uD569\uB2C8\uB2E4.\n"));
          state = structuredClone(INITIAL_WIZARD_STATE);
        }
      } else {
        state = structuredClone(INITIAL_WIZARD_STATE);
      }
    } else {
      state = structuredClone(INITIAL_WIZARD_STATE);
    }
    if (state.currentStep === 0) {
      console.log(chalk13.bold("\n\u{1F680} ClickEye AI \uC194\uB8E8\uC158 \uC704\uC800\uB4DC\n"));
    }
    console.log(
      chalk13.dim(
        "Ctrl+C\uB85C \uC911\uB2E8\uD558\uBA74 \uC790\uB3D9 \uC800\uC7A5\uB429\uB2C8\uB2E4. `ce init`\uC73C\uB85C \uC7AC\uAC1C\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\n"
      )
    );
  }
  process.once("SIGINT", async () => {
    if (state.sessionId) {
      await saveSession(state);
      console.log(
        chalk13.yellow(
          `
\u23F8  \uC138\uC158 \uC800\uC7A5\uB428. \uC7AC\uAC1C\uD558\uB824\uBA74:
  ce init --resume ${state.sessionId}
`
        )
      );
    }
    process.exit(0);
  });
  try {
    for (let step = state.currentStep; step < STEP_RUNNERS.length; step++) {
      const runner = STEP_RUNNERS[step];
      if (!runner) break;
      state = await runner(state);
      await saveSession(state);
    }
    if (state.currentStep >= STEP_RUNNERS.length) {
      console.log(chalk13.bold.green("\n\u2705 \uC704\uC800\uB4DC \uC644\uB8CC!\n"));
    }
  } catch (err) {
    if (err instanceof AuthRequiredError) {
      console.error(chalk13.red(`
\u274C ${err.message}
`));
      process.exit(1);
    }
    console.error(chalk13.red(`
\u274C \uC624\uB958 \uBC1C\uC0DD: ${String(err)}
`));
    if (state.sessionId) {
      await saveSession(state);
      console.log(
        chalk13.dim(`\uC138\uC158 \uC800\uC7A5\uB428. \uC7AC\uAC1C: ce init --resume ${state.sessionId}`)
      );
    }
    process.exit(1);
  }
}

// src/commands/doctor.ts
import fs from "fs/promises";
import path from "path";
import chalk14 from "chalk";
async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}
async function isExecutable(filePath) {
  try {
    await fs.access(filePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}
async function checkClaudeDir(targetDir) {
  const exists = await fileExists(path.join(targetDir, ".claude"));
  return {
    label: ".claude/ \uB514\uB809\uD1A0\uB9AC \uC874\uC7AC",
    passed: exists,
    detail: exists ? void 0 : "ce init\uC744 \uBA3C\uC800 \uC2E4\uD589\uD558\uC138\uC694"
  };
}
async function checkSettingsJson(targetDir) {
  const settingsPath = path.join(targetDir, ".claude/settings.json");
  if (!await fileExists(settingsPath)) {
    return {
      label: "settings.json \uC874\uC7AC",
      passed: false,
      detail: "ce init\uC744 \uBA3C\uC800 \uC2E4\uD589\uD558\uC138\uC694"
    };
  }
  try {
    const raw = await fs.readFile(settingsPath, "utf-8");
    const settings = JSON.parse(raw);
    const hasPermissions = settings.permissions != null;
    const hasHooks = settings.hooks != null;
    if (!hasPermissions || !hasHooks) {
      const missing = [];
      if (!hasPermissions) missing.push("permissions");
      if (!hasHooks) missing.push("hooks");
      return {
        label: "settings.json \uC720\uD6A8\uC131",
        passed: false,
        detail: `\uD544\uC218 \uD544\uB4DC \uB204\uB77D: ${missing.join(", ")}`
      };
    }
    return { label: "settings.json \uC720\uD6A8\uC131", passed: true };
  } catch (error) {
    return {
      label: "settings.json \uC720\uD6A8\uC131",
      passed: false,
      detail: error instanceof SyntaxError ? "JSON \uD30C\uC2F1 \uC2E4\uD328 \u2014 \uC62C\uBC14\uB978 JSON \uD615\uC2DD\uC778\uC9C0 \uD655\uC778\uD558\uC138\uC694" : "\uD30C\uC77C \uC77D\uAE30 \uC2E4\uD328"
    };
  }
}
async function checkHookScripts(targetDir) {
  const results = [];
  const scriptsDir = path.join(targetDir, "scripts");
  if (!await fileExists(scriptsDir)) {
    return [];
  }
  const entries = await fs.readdir(scriptsDir);
  const shellScripts = entries.filter((e) => e.endsWith(".sh"));
  for (const script of shellScripts) {
    const scriptPath = path.join(scriptsDir, script);
    const executable = await isExecutable(scriptPath);
    results.push({
      label: `scripts/${script} \uC2E4\uD589 \uAD8C\uD55C`,
      passed: executable,
      detail: executable ? void 0 : `chmod +x scripts/${script} \uC73C\uB85C \uAD8C\uD55C\uC744 \uBD80\uC5EC\uD558\uC138\uC694`
    });
  }
  return results;
}
async function checkAgentReferences(targetDir) {
  const results = [];
  const claudeMdPath = path.join(targetDir, "CLAUDE.md");
  if (!await fileExists(claudeMdPath)) {
    return [
      {
        label: "CLAUDE.md \uC874\uC7AC",
        passed: false,
        detail: "ce init\uC73C\uB85C \uC0DD\uC131\uD558\uC138\uC694"
      }
    ];
  }
  const claudeMd = await fs.readFile(claudeMdPath, "utf-8");
  const agentRefs = claudeMd.match(/\.claude\/agents\/[\w-]+\.md/g) ?? [];
  for (const ref of agentRefs) {
    const refPath = path.join(targetDir, ref);
    const exists = await fileExists(refPath);
    results.push({
      label: `${ref} \uCC38\uC870 \uBB34\uACB0\uC131`,
      passed: exists,
      detail: exists ? void 0 : `\uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. ce add agent <id>\uB85C \uCD94\uAC00\uD558\uC138\uC694`
    });
  }
  if (agentRefs.length === 0) {
    results.push({
      label: "\uC5D0\uC774\uC804\uD2B8 \uD30C\uC77C \uCC38\uC870",
      passed: true,
      detail: "CLAUDE.md\uC5D0 \uC5D0\uC774\uC804\uD2B8 \uCC38\uC870 \uC5C6\uC74C (\uC815\uC0C1)"
    });
  }
  return results;
}
async function checkEnvVars(targetDir) {
  const results = [];
  const envPath = path.join(targetDir, ".env");
  if (!await fileExists(envPath)) {
    const examplePath = path.join(targetDir, ".env.example");
    if (await fileExists(examplePath)) {
      results.push({
        label: ".env \uD30C\uC77C \uC874\uC7AC",
        passed: false,
        detail: ".env.example\uC744 \uBCF5\uC0AC\uD558\uC5EC .env\uB97C \uC0DD\uC131\uD558\uC138\uC694"
      });
    }
    return results;
  }
  return results;
}
async function checkClaudeMd(targetDir) {
  const exists = await fileExists(path.join(targetDir, "CLAUDE.md"));
  return {
    label: "CLAUDE.md \uC874\uC7AC",
    passed: exists,
    detail: exists ? void 0 : "ce init\uC73C\uB85C \uC0DD\uC131\uD558\uC138\uC694"
  };
}
async function doctorCommand() {
  const targetDir = process.cwd();
  console.log(chalk14.bold("\n\u{1F50D} ClickEye \uC124\uC815 \uC9C4\uB2E8\n"));
  console.log(chalk14.dim(`\uAC80\uC0AC \uACBD\uB85C: ${targetDir}
`));
  const allResults = [];
  allResults.push(await checkClaudeDir(targetDir));
  allResults.push(await checkClaudeMd(targetDir));
  allResults.push(await checkSettingsJson(targetDir));
  allResults.push(...await checkHookScripts(targetDir));
  allResults.push(...await checkAgentReferences(targetDir));
  allResults.push(...await checkEnvVars(targetDir));
  let passCount = 0;
  let failCount = 0;
  for (const result of allResults) {
    const icon = result.passed ? chalk14.green("\u2705") : chalk14.red("\u274C");
    console.log(`${icon} ${result.label}`);
    if (result.detail) {
      console.log(chalk14.dim(`   \u2192 ${result.detail}`));
    }
    if (result.passed) passCount++;
    else failCount++;
  }
  console.log(chalk14.bold("\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"));
  if (failCount === 0) {
    console.log(
      chalk14.green(`
\u{1F389} \uBAA8\uB4E0 \uAC80\uC0AC \uD1B5\uACFC! (${passCount}/${passCount})`)
    );
  } else {
    console.log(
      chalk14.yellow(
        `
\u26A0\uFE0F  ${failCount}\uAC1C \uD56D\uBAA9 \uC2E4\uD328 (${passCount}/${passCount + failCount} \uD1B5\uACFC)`
      )
    );
    console.log(
      chalk14.dim(
        "\n\uC704 \u274C \uD56D\uBAA9\uC758 \uC548\uB0B4\uB97C \uB530\uB77C \uBB38\uC81C\uB97C \uD574\uACB0\uD558\uC138\uC694."
      )
    );
  }
  console.log();
}

// src/auth/login.ts
import inquirer12 from "inquirer";
import chalk15 from "chalk";
async function loginCommand() {
  console.log(chalk15.bold("\n\u{1F510} ClickEye \uB85C\uADF8\uC778\n"));
  const existing = await loadCredentials();
  if (existing) {
    const { proceed } = await inquirer12.prompt([
      {
        type: "confirm",
        name: "proceed",
        message: `\uC774\uBBF8 ${chalk15.cyan(existing.email)}(\uC73C)\uB85C \uB85C\uADF8\uC778\uB418\uC5B4 \uC788\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uB85C\uADF8\uC778\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?`,
        default: false
      }
    ]);
    if (!proceed) return;
  }
  const { email, password } = await inquirer12.prompt([
    {
      type: "input",
      name: "email",
      message: "\uC774\uBA54\uC77C:",
      validate: (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || "\uC720\uD6A8\uD55C \uC774\uBA54\uC77C\uC744 \uC785\uB825\uD574 \uC8FC\uC138\uC694"
    },
    {
      type: "password",
      name: "password",
      message: "\uBE44\uBC00\uBC88\uD638:",
      mask: "*"
    }
  ]);
  try {
    const res = await apiClient.post(
      "/api/v1/auth/login",
      { email, password },
      false
      // 로그인은 인증 불필요
    );
    await saveCredentials({
      access_token: res.access_token,
      refresh_token: res.refresh_token,
      email,
      expires_at: decodeJwtExpiry(res.access_token)
    });
    console.log(chalk15.green(`
\u2705 ${email}\uC73C\uB85C \uB85C\uADF8\uC778\uB418\uC5C8\uC2B5\uB2C8\uB2E4.
`));
  } catch (err) {
    const msg = err instanceof Error ? err.message : "\uB85C\uADF8\uC778\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4";
    console.error(chalk15.red(`
\u274C ${msg}
`));
    process.exit(1);
  }
}
async function logoutCommand() {
  const creds = await loadCredentials();
  if (!creds) {
    console.log(chalk15.yellow("\uD604\uC7AC \uB85C\uADF8\uC778 \uC0C1\uD0DC\uAC00 \uC544\uB2D9\uB2C8\uB2E4."));
    return;
  }
  await clearCredentials();
  clearCatalogCache();
  console.log(chalk15.green(`
\u2705 ${creds.email} \uB85C\uADF8\uC544\uC6C3\uB418\uC5C8\uC2B5\uB2C8\uB2E4.
`));
}

// src/commands/list.ts
import chalk16 from "chalk";
var VALID_CATEGORIES = [
  "agents",
  "skills",
  "hooks",
  "platforms",
  "pipelines"
];
function getLabel(item) {
  return item.label;
}
function getDescription(item) {
  return "description" in item && item.description ? item.description : "";
}
function getSlug(item) {
  return "slug" in item ? item.slug : item.id;
}
async function listCommand(category) {
  if (!VALID_CATEGORIES.includes(category)) {
    console.error(
      chalk16.red(
        `\u274C \uC54C \uC218 \uC5C6\uB294 \uCE74\uD14C\uACE0\uB9AC: ${category}
   \uC0AC\uC6A9 \uAC00\uB2A5: ${VALID_CATEGORIES.join(" | ")}`
      )
    );
    process.exit(1);
  }
  try {
    const items = await fetchCatalog(category);
    if (items.length === 0) {
      console.log(chalk16.yellow(`
${category} \uCE74\uD0C8\uB85C\uADF8\uAC00 \uBE44\uC5B4 \uC788\uC2B5\uB2C8\uB2E4.
`));
      return;
    }
    console.log(chalk16.bold(`
\u{1F4E6} ${category} (${items.length}\uAC1C)
`));
    for (const item of items) {
      const slug = getSlug(item);
      const label = getLabel(item);
      const desc = getDescription(item);
      console.log(
        `  ${chalk16.cyan(slug.padEnd(22))} ${chalk16.white(label)}`
      );
      if (desc) {
        console.log(`  ${" ".repeat(22)} ${chalk16.dim(desc)}`);
      }
    }
    console.log();
  } catch (err) {
    if (err instanceof AuthRequiredError) {
      console.error(chalk16.red(`
\u274C ${err.message}
`));
    } else if (err instanceof ApiError) {
      console.error(chalk16.red(`
\u274C API \uC624\uB958 (${err.status}): ${err.message}
`));
    } else {
      console.error(chalk16.red(`
\u274C \uCE74\uD0C8\uB85C\uADF8 \uC870\uD68C \uC2E4\uD328: ${String(err)}
`));
    }
    process.exit(1);
  }
}

// src/commands/redownload.ts
import chalk17 from "chalk";
import ora6 from "ora";
async function redownloadCommand(projectId, flags) {
  const creds = await loadCredentials();
  if (!creds) {
    console.error(
      chalk17.red("\n\u274C \uC778\uC99D\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. `ce login`\uC744 \uBA3C\uC800 \uC2E4\uD589\uD574 \uC8FC\uC138\uC694.\n")
    );
    process.exit(1);
  }
  const envVars = {};
  if (flags.envFile) {
    const { readFile: readFile3 } = await import("fs/promises");
    try {
      const content = await readFile3(flags.envFile, "utf-8");
      for (const line of content.split("\n")) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const eqIdx = trimmed.indexOf("=");
        if (eqIdx === -1) continue;
        const key = trimmed.slice(0, eqIdx).trim();
        const value = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
        if (key) envVars[key] = value;
      }
    } catch {
      console.error(chalk17.red(`
\u274C \uD658\uACBD \uD30C\uC77C\uC744 \uC77D\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4: ${flags.envFile}
`));
      process.exit(1);
    }
  }
  const projectName = flags.name ?? projectId;
  const destDir = flags.output ?? process.cwd();
  const spinner = ora6("\uD504\uB85C\uC81D\uD2B8 ZIP\uC744 \uB2E4\uC6B4\uB85C\uB4DC\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4...").start();
  try {
    const projectDir = await downloadAndExtract(
      projectId,
      envVars,
      projectName,
      destDir,
      true
    );
    spinner.succeed(`\uC555\uCD95 \uD574\uC81C \uC644\uB8CC: ${projectDir}`);
    console.log(chalk17.bold.green("\n\u2705 \uC7AC\uB2E4\uC6B4\uB85C\uB4DC \uC644\uB8CC!\n"));
  } catch (err) {
    spinner.fail("\uB2E4\uC6B4\uB85C\uB4DC \uC2E4\uD328");
    console.error(chalk17.red(`
\u274C ${String(err)}
`));
    process.exit(1);
  }
}

// src/cli.ts
var program = new Command();
program.name("ce").description(
  "ClickEye CLI \u2014 AI \uC194\uB8E8\uC158 \uBE4C\uB354 (clickeye.ai \uC704\uC800\uB4DC\uC758 \uD130\uBBF8\uB110 \uBC84\uC804)"
).version("1.0.0");
program.command("init").description("12\uB2E8\uACC4 \uC704\uC800\uB4DC\uB85C AI \uC194\uB8E8\uC158\uC744 \uC124\uACC4\uD558\uACE0 ZIP\uC744 \uB2E4\uC6B4\uB85C\uB4DC\uD569\uB2C8\uB2E4").option("--resume <sessionId>", "\uC774\uC804 \uC138\uC158 ID\uB85C \uC7AC\uAC1C\uD569\uB2C8\uB2E4").action(initCommand);
program.command("list").description("\uCE74\uD0C8\uB85C\uADF8 \uD56D\uBAA9\uC744 \uC870\uD68C\uD569\uB2C8\uB2E4").argument("<category>", "\uC870\uD68C\uD560 \uC720\uD615 (agents | skills | hooks | platforms | pipelines)").action(listCommand);
program.command("doctor").description("\uD604\uC7AC \uD504\uB85C\uC81D\uD2B8\uC758 ClickEye \uC124\uC815 \uC0C1\uD0DC\uB97C \uC9C4\uB2E8\uD569\uB2C8\uB2E4").action(doctorCommand);
program.command("login").description("ClickEye \uACC4\uC815\uC73C\uB85C \uB85C\uADF8\uC778\uD569\uB2C8\uB2E4").action(loginCommand);
program.command("logout").description("\uD604\uC7AC \uACC4\uC815\uC5D0\uC11C \uB85C\uADF8\uC544\uC6C3\uD569\uB2C8\uB2E4").action(logoutCommand);
program.command("redownload").description("\uAE30\uC874 \uD504\uB85C\uC81D\uD2B8\uC758 ZIP\uC744 \uC7AC\uB2E4\uC6B4\uB85C\uB4DC\uD558\uACE0 \uC555\uCD95 \uD574\uC81C\uD569\uB2C8\uB2E4").argument("<projectId>", "\uC7AC\uB2E4\uC6B4\uB85C\uB4DC\uD560 \uD504\uB85C\uC81D\uD2B8 UUID").option("--env-file <path>", ".env \uD30C\uC77C\uC5D0\uC11C \uD658\uACBD \uBCC0\uC218\uB97C \uC77D\uC5B4\uC635\uB2C8\uB2E4").option("--output <dir>", "\uC555\uCD95 \uD574\uC81C \uB300\uC0C1 \uB514\uB809\uD1A0\uB9AC (\uAE30\uBCF8\uAC12: \uD604\uC7AC \uB514\uB809\uD1A0\uB9AC)").option("--name <name>", "\uC555\uCD95 \uD574\uC81C \uB514\uB809\uD1A0\uB9AC\uBA85 (\uAE30\uBCF8\uAC12: \uD504\uB85C\uC81D\uD2B8 ID)").action(
  (projectId, flags) => redownloadCommand(projectId, flags)
);
program.parse();
//# sourceMappingURL=cli.js.map