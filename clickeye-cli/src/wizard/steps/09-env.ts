import inquirer from "inquirer";
import chalk from "chalk";
import ora from "ora";
import { apiClient } from "../../api/client.js";
import { fetchSkills } from "../../api/catalog.js";
import type { WizardState } from "../state.js";

interface ValidationResponse {
  valid: boolean;
  message: string;
}

async function validateLinear(apiKey: string, teamId: string): Promise<ValidationResponse> {
  return apiClient.post<ValidationResponse>("/api/v1/integrations/validate/linear", {
    api_key: apiKey,
    team_id: teamId,
  });
}

async function validateNotion(apiKey: string, databaseId: string): Promise<ValidationResponse> {
  return apiClient.post<ValidationResponse>("/api/v1/integrations/validate/notion", {
    api_key: apiKey,
    database_id: databaseId,
  });
}

export async function step09Env(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n⚙️  Step 9 — 환경 설정\n"));

  // ── Claude 인증 방식 선택 ─────────────────────────────────────────────────
  const { authMethod } = await inquirer.prompt<{
    authMethod: "api_key" | "oauth_browser" | "oauth_setup_token";
  }>([
    {
      type: "list",
      name: "authMethod",
      message: "Claude 인증 방식을 선택해 주세요:",
      choices: [
        {
          name: `${chalk.cyan("API Key")}            Anthropic API 키를 직접 사용`,
          value: "api_key",
        },
        {
          name: `${chalk.cyan("OAuth (브라우저)")}   브라우저로 Claude.ai 로그인 (Pro/Max 계정)`,
          value: "oauth_browser",
        },
        {
          name: `${chalk.cyan("OAuth (Setup Token)")} 서버 환경용 Claude OAuth 토큰`,
          value: "oauth_setup_token",
        },
      ],
    },
  ]);

  const envVars: Record<string, string> = {};

  if (authMethod === "api_key") {
    const { apiKey } = await inquirer.prompt<{ apiKey: string }>([
      {
        type: "password",
        name: "apiKey",
        message: "Anthropic API 키를 입력해 주세요 (sk-ant-...):",
        validate: (v: string) =>
          v.trim().startsWith("sk-") ? true : "올바른 API 키 형식이 아닙니다 (sk-로 시작해야 합니다)",
      },
    ]);
    envVars["ANTHROPIC_API_KEY"] = apiKey.trim();
  } else if (authMethod === "oauth_setup_token") {
    const { setupToken } = await inquirer.prompt<{ setupToken: string }>([
      {
        type: "password",
        name: "setupToken",
        message: "Claude OAuth Setup Token을 입력해 주세요:",
        validate: (v: string) => (v.trim().length > 0 ? true : "토큰을 입력해 주세요"),
      },
    ]);
    envVars["CLAUDE_OAUTH_SETUP_TOKEN"] = setupToken.trim();
  }

  // ── 선택된 스킬의 통합 검증 ──────────────────────────────────────────────
  const allSkills = await fetchSkills();
  const selectedSkillObjects = allSkills.filter((s) =>
    state.agents.selectedSkills.includes(s.id),
  );
  const selectedSlugs = selectedSkillObjects.map((s) => s.slug);

  const LINEAR_SLUGS = new Set(["linear-reader", "linear-writer"]);
  const NOTION_SLUGS = new Set(["notion-reader", "notion-writer"]);
  const hasLinear = selectedSlugs.some((slug) => LINEAR_SLUGS.has(slug));
  const hasNotion = selectedSlugs.some((slug) => NOTION_SLUGS.has(slug));

  const MAX_VALIDATION_ATTEMPTS = 3;

  if (hasLinear) {
    console.log(chalk.bold("\n📋 Linear 통합 설정:\n"));
    let linearValid = false;
    let linearAttempts = 0;
    while (!linearValid) {
      if (linearAttempts >= MAX_VALIDATION_ATTEMPTS) {
        console.log(chalk.red(`\n❌ Linear 검증 ${MAX_VALIDATION_ATTEMPTS}회 실패. 위저드를 종료합니다.`));
        process.exit(1);
      }
      linearAttempts++;

      const { linearApiKey, linearTeamId } = await inquirer.prompt<{
        linearApiKey: string;
        linearTeamId: string;
      }>([
        {
          type: "password",
          name: "linearApiKey",
          message: "Linear API 키 (lin_api_...):",
          validate: (v: string) =>
            v.trim().startsWith("lin_api_") ? true : "Linear API 키는 lin_api_로 시작해야 합니다",
        },
        {
          type: "input",
          name: "linearTeamId",
          message: "Linear 팀 ID (UUID):",
          validate: (v: string) => (v.trim().length > 0 ? true : "팀 ID를 입력해 주세요"),
        },
      ]);

      const spinner = ora("Linear API 키 검증 중...").start();
      try {
        const result = await validateLinear(linearApiKey.trim(), linearTeamId.trim());
        if (result.valid) {
          spinner.succeed("Linear 연결 확인됨");
          envVars["LINEAR_API_KEY"] = linearApiKey.trim();
          envVars["LINEAR_TEAM_ID"] = linearTeamId.trim();
          linearValid = true;
        } else {
          spinner.fail(`Linear 검증 실패: ${result.message}`);
          console.log(chalk.yellow(`  다시 입력해 주세요. (${linearAttempts}/${MAX_VALIDATION_ATTEMPTS})\n`));
        }
      } catch {
        spinner.fail("Linear API 검증 중 오류가 발생했습니다.");
        console.log(chalk.yellow(`  다시 입력해 주세요. (${linearAttempts}/${MAX_VALIDATION_ATTEMPTS})\n`));
      }
    }
  }

  if (hasNotion) {
    console.log(chalk.bold("\n📓 Notion 통합 설정:\n"));
    let notionValid = false;
    let notionAttempts = 0;
    while (!notionValid) {
      if (notionAttempts >= MAX_VALIDATION_ATTEMPTS) {
        console.log(chalk.red(`\n❌ Notion 검증 ${MAX_VALIDATION_ATTEMPTS}회 실패. 위저드를 종료합니다.`));
        process.exit(1);
      }
      notionAttempts++;

      const { notionApiKey, notionDatabaseId } = await inquirer.prompt<{
        notionApiKey: string;
        notionDatabaseId: string;
      }>([
        {
          type: "password",
          name: "notionApiKey",
          message: "Notion API 키 (secret_...):",
          validate: (v: string) =>
            v.trim().startsWith("secret_") ? true : "Notion API 키는 secret_로 시작해야 합니다",
        },
        {
          type: "input",
          name: "notionDatabaseId",
          message: "Notion 데이터베이스 ID (UUID):",
          validate: (v: string) => (v.trim().length > 0 ? true : "데이터베이스 ID를 입력해 주세요"),
        },
      ]);

      const spinner = ora("Notion API 키 검증 중...").start();
      try {
        const result = await validateNotion(notionApiKey.trim(), notionDatabaseId.trim());
        if (result.valid) {
          spinner.succeed("Notion 연결 확인됨");
          envVars["NOTION_API_KEY"] = notionApiKey.trim();
          envVars["NOTION_DATABASE_ID"] = notionDatabaseId.trim();
          notionValid = true;
        } else {
          spinner.fail(`Notion 검증 실패: ${result.message}`);
          console.log(chalk.yellow(`  다시 입력해 주세요. (${notionAttempts}/${MAX_VALIDATION_ATTEMPTS})\n`));
        }
      } catch {
        spinner.fail("Notion API 검증 중 오류가 발생했습니다.");
        console.log(chalk.yellow(`  다시 입력해 주세요. (${notionAttempts}/${MAX_VALIDATION_ATTEMPTS})\n`));
      }
    }
  }

  // ── 기타 필수 env_var 수집 ────────────────────────────────────────────────
  for (const skill of selectedSkillObjects) {
    const requiredVars = (skill.env_vars ?? []).filter(
      (ev) => ev.required && !envVars[ev.name],
    );
    for (const ev of requiredVars) {
      const desc = ev.description ? chalk.dim(` (${ev.description})`) : "";
      const { value } = await inquirer.prompt<{ value: string }>([
        {
          type: "password",
          name: "value",
          message: `${ev.name}${desc}:`,
          validate: (v: string) => (v.trim().length > 0 ? true : `${ev.name}을 입력해 주세요`),
        },
      ]);
      envVars[ev.name] = value.trim();
    }
  }

  console.log(chalk.dim(`\n✅ 환경 설정 완료 (${Object.keys(envVars).length}개 변수 설정됨)\n`));

  return {
    ...state,
    currentStep: 10,
    env: { authMethod, envVars },
  };
}
