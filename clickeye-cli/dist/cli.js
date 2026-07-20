// src/cli.ts
import { Command } from "commander";

// src/commands/doctor.ts
import fs from "fs/promises";
import path from "path";
import chalk from "chalk";
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
  console.log(chalk.bold("\n\u{1F50D} ClickEye \uC124\uC815 \uC9C4\uB2E8\n"));
  console.log(chalk.dim(`\uAC80\uC0AC \uACBD\uB85C: ${targetDir}
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
    const icon = result.passed ? chalk.green("\u2705") : chalk.red("\u274C");
    console.log(`${icon} ${result.label}`);
    if (result.detail) {
      console.log(chalk.dim(`   \u2192 ${result.detail}`));
    }
    if (result.passed) passCount++;
    else failCount++;
  }
  console.log(chalk.bold("\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"));
  if (failCount === 0) {
    console.log(
      chalk.green(`
\u{1F389} \uBAA8\uB4E0 \uAC80\uC0AC \uD1B5\uACFC! (${passCount}/${passCount})`)
    );
  } else {
    console.log(
      chalk.yellow(
        `
\u26A0\uFE0F  ${failCount}\uAC1C \uD56D\uBAA9 \uC2E4\uD328 (${passCount}/${passCount + failCount} \uD1B5\uACFC)`
      )
    );
    console.log(
      chalk.dim(
        "\n\uC704 \u274C \uD56D\uBAA9\uC758 \uC548\uB0B4\uB97C \uB530\uB77C \uBB38\uC81C\uB97C \uD574\uACB0\uD558\uC138\uC694."
      )
    );
  }
  console.log();
}

// src/auth/login.ts
import inquirer from "inquirer";
import chalk2 from "chalk";

// src/config.ts
var API_BASE_URL = process.env["CLICKEYE_API_URL"] ?? "https://api.clickeye.ai";

// src/auth/credentials.ts
import { readFile, writeFile, unlink, mkdir, chmod } from "fs/promises";
import { homedir } from "os";
import { join } from "path";
function credDir() {
  return join(homedir(), ".config", "clickeye");
}
function credFile() {
  return join(credDir(), "credentials.json");
}
async function loadCredentials() {
  try {
    const raw = await readFile(credFile(), "utf8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
async function saveCredentials(creds) {
  await mkdir(credDir(), { recursive: true, mode: 448 });
  await writeFile(credFile(), JSON.stringify(creds, null, 2), {
    encoding: "utf8",
    mode: 384
  });
  await chmod(credFile(), 384);
}
async function clearCredentials() {
  try {
    await unlink(credFile());
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

// src/auth/login.ts
async function loginCommand() {
  console.log(chalk2.bold("\n\u{1F510} ClickEye \uB85C\uADF8\uC778\n"));
  const existing = await loadCredentials();
  if (existing) {
    const { proceed } = await inquirer.prompt([
      {
        type: "confirm",
        name: "proceed",
        message: `\uC774\uBBF8 ${chalk2.cyan(existing.email)}(\uC73C)\uB85C \uB85C\uADF8\uC778\uB418\uC5B4 \uC788\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uB85C\uADF8\uC778\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?`,
        default: false
      }
    ]);
    if (!proceed) return;
  }
  const { email, password } = await inquirer.prompt([
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
    console.log(chalk2.green(`
\u2705 ${email}\uC73C\uB85C \uB85C\uADF8\uC778\uB418\uC5C8\uC2B5\uB2C8\uB2E4.
`));
  } catch (err) {
    const msg = err instanceof Error ? err.message : "\uB85C\uADF8\uC778\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4";
    console.error(chalk2.red(`
\u274C ${msg}
`));
    process.exit(1);
  }
}
async function logoutCommand() {
  const creds = await loadCredentials();
  if (!creds) {
    console.log(chalk2.yellow("\uD604\uC7AC \uB85C\uADF8\uC778 \uC0C1\uD0DC\uAC00 \uC544\uB2D9\uB2C8\uB2E4."));
    return;
  }
  await clearCredentials();
  clearCatalogCache();
  console.log(chalk2.green(`
\u2705 ${creds.email} \uB85C\uADF8\uC544\uC6C3\uB418\uC5C8\uC2B5\uB2C8\uB2E4.
`));
}

// src/commands/list.ts
import chalk3 from "chalk";
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
      chalk3.red(
        `\u274C \uC54C \uC218 \uC5C6\uB294 \uCE74\uD14C\uACE0\uB9AC: ${category}
   \uC0AC\uC6A9 \uAC00\uB2A5: ${VALID_CATEGORIES.join(" | ")}`
      )
    );
    process.exit(1);
  }
  try {
    const items = await fetchCatalog(category);
    if (items.length === 0) {
      console.log(chalk3.yellow(`
${category} \uCE74\uD0C8\uB85C\uADF8\uAC00 \uBE44\uC5B4 \uC788\uC2B5\uB2C8\uB2E4.
`));
      return;
    }
    console.log(chalk3.bold(`
\u{1F4E6} ${category} (${items.length}\uAC1C)
`));
    for (const item of items) {
      const slug = getSlug(item);
      const label = getLabel(item);
      const desc = getDescription(item);
      console.log(
        `  ${chalk3.cyan(slug.padEnd(22))} ${chalk3.white(label)}`
      );
      if (desc) {
        console.log(`  ${" ".repeat(22)} ${chalk3.dim(desc)}`);
      }
    }
    console.log();
  } catch (err) {
    if (err instanceof AuthRequiredError) {
      console.error(chalk3.red(`
\u274C ${err.message}
`));
    } else if (err instanceof ApiError) {
      console.error(chalk3.red(`
\u274C API \uC624\uB958 (${err.status}): ${err.message}
`));
    } else {
      console.error(chalk3.red(`
\u274C \uCE74\uD0C8\uB85C\uADF8 \uC870\uD68C \uC2E4\uD328: ${String(err)}
`));
    }
    process.exit(1);
  }
}

// src/cli.ts
var program = new Command();
program.name("ce").description("ClickEye CLI \u2014 \uCE74\uD0C8\uB85C\uADF8 \uC870\uD68C \uBC0F \uD504\uB85C\uC81D\uD2B8 \uC124\uC815 \uC9C4\uB2E8 \uB3C4\uAD6C").version("1.0.0");
program.command("list").description("\uCE74\uD0C8\uB85C\uADF8 \uD56D\uBAA9\uC744 \uC870\uD68C\uD569\uB2C8\uB2E4").argument("<category>", "\uC870\uD68C\uD560 \uC720\uD615 (agents | skills | hooks | platforms | pipelines)").action(listCommand);
program.command("doctor").description("\uD604\uC7AC \uD504\uB85C\uC81D\uD2B8\uC758 ClickEye \uC124\uC815 \uC0C1\uD0DC\uB97C \uC9C4\uB2E8\uD569\uB2C8\uB2E4").action(doctorCommand);
program.command("login").description("ClickEye \uACC4\uC815\uC73C\uB85C \uB85C\uADF8\uC778\uD569\uB2C8\uB2E4").action(loginCommand);
program.command("logout").description("\uD604\uC7AC \uACC4\uC815\uC5D0\uC11C \uB85C\uADF8\uC544\uC6C3\uD569\uB2C8\uB2E4").action(logoutCommand);
program.parse();
//# sourceMappingURL=cli.js.map