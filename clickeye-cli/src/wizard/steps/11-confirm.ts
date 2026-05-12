import inquirer from "inquirer";
import chalk from "chalk";
import ora from "ora";
import { apiClient } from "../../api/client.js";
import { downloadAndExtract } from "../../api/download.js";
import { deleteSession } from "../session.js";
import type { WizardState } from "../state.js";

interface FinalizeResponse {
  project_id: string;
  project_name: string;
  session_id: string;
  message: string;
  initial_task_url: string | null;
}

export async function step11Confirm(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n✅ Step 11 — 최종 확인\n"));

  // ── 설정 요약 출력 ────────────────────────────────────────────────────────
  const selectedPM = state.pm.recommendedPMs.find(
    (p) => p.pmId === state.pm.selectedPmProfileId,
  );
  const selectedProto = state.prototypes.prototypes.find(
    (p) => p.id === state.prototypes.selectedPrototypeId,
  );

  console.log(chalk.bold("  📋 설정 요약:"));
  console.log(`     회사명:       ${chalk.cyan(state.company.companyName)}`);
  console.log(`     프로토타입:   ${chalk.cyan(selectedProto?.title ?? state.prototypes.selectedPrototypeId ?? "-")}`);
  console.log(`     PM:            ${chalk.cyan(selectedPM?.name ?? state.pm.selectedPmProfileId ?? "-")}`);
  console.log(`     에이전트:     ${chalk.cyan(String(state.agents.selectedAgents.length))}개`);
  console.log(`     스킬:         ${chalk.cyan(String(state.agents.selectedSkills.length))}개`);
  console.log(`     훅:           ${chalk.cyan(String(state.agents.selectedHooks.length))}개`);
  console.log(`     플랫폼:       ${chalk.cyan(state.platform.platformId ?? "-")}`);
  console.log(`     인증방식:     ${chalk.cyan(state.env.authMethod ?? "-")}`);
  console.log();

  // ── 프로젝트 이름 입력 ───────────────────────────────────────────────────
  const defaultName = state.company.companyName
    ? `${state.company.companyName.replace(/\s+/g, "-").toLowerCase()}-solution`
    : "clickeye-solution";

  const { projectName } = await inquirer.prompt<{ projectName: string }>([
    {
      type: "input",
      name: "projectName",
      message: "프로젝트 이름:",
      default: defaultName,
      validate: (v: string) =>
        v.trim().length > 0 ? true : "프로젝트 이름을 입력해 주세요",
    },
  ]);

  const { confirmed } = await inquirer.prompt<{ confirmed: boolean }>([
    {
      type: "confirm",
      name: "confirmed",
      message: "이 설정으로 프로젝트를 생성하시겠습니까?",
      default: true,
    },
  ]);

  if (!confirmed) {
    console.log(
      chalk.yellow(
        "\n⬅️  취소됨. 재시도하려면 `ce init --resume` 옵션을 사용하세요.\n",
      ),
    );
    process.exit(0);
  }

  // ── 미입력 환경 변수 수집 (finalize 전 — linear/notion 키가 finalize 페이로드에 포함되어야 함)
  const deferred = state.env.deferredEnvVars ?? [];
  const finalEnvVars = { ...state.env.envVars };

  if (deferred.length > 0) {
    console.log(
      chalk.yellow(
        "\n⚠️  다음 환경 변수가 아직 입력되지 않았습니다.\n" +
        "   지금 입력하거나 Enter로 건너뛸 수 있습니다.\n",
      ),
    );
    for (const varName of deferred) {
      const { value } = await inquirer.prompt<{ value: string }>([
        {
          type: "password",
          name: "value",
          message: `${varName}:`,
        },
      ]);
      if (value.trim()) {
        finalEnvVars[varName] = value.trim();
      }
    }
    console.log();
  }

  // ── 다운로드 차단 게이트 — deferred 키가 모두 채워질 때까지 ZIP 다운로드 금지 ──
  let missingVars = deferred.filter((v) => !finalEnvVars[v]);

  while (missingVars.length > 0) {
    console.log(
      chalk.red(
        "\n🚫 ZIP을 다운로드하려면 다음 환경 변수를 반드시 입력해야 합니다:\n" +
          missingVars.map((v) => `   • ${v}`).join("\n"),
      ),
    );

    const { action } = await inquirer.prompt<{ action: "enter" | "cancel" }>([
      {
        type: "list",
        name: "action",
        message: "어떻게 하시겠습니까?",
        choices: [
          { name: "지금 입력하기", value: "enter" },
          { name: "취소 (세션 저장 후 나중에 재개)", value: "cancel" },
        ],
      },
    ]);

    if (action === "cancel") {
      console.log(chalk.yellow("\n⏸  세션이 저장됩니다. `ce init`으로 재개하세요.\n"));
      process.exit(0);
    }

    for (const varName of missingVars) {
      const { value } = await inquirer.prompt<{ value: string }>([
        {
          type: "password",
          name: "value",
          message: `${varName}:`,
          validate: (v: string) => v.trim().length > 0 ? true : "값을 입력해야 합니다",
        },
      ]);
      finalEnvVars[varName] = value.trim();
    }

    missingVars = deferred.filter((v) => !finalEnvVars[v]);
  }

  // ── Finalize 호출 ─────────────────────────────────────────────────────────
  const spinner = ora("프로젝트를 생성하고 있습니다...").start();
  let finalizeResult: FinalizeResponse;
  try {
    finalizeResult = await apiClient.post<FinalizeResponse>(
      `/api/v1/prototype-sessions/${state.sessionId}/finalize`,
      {
        project_name: projectName.trim(),
        linear_api_key: finalEnvVars["LINEAR_API_KEY"] ?? null,
        linear_team_id: finalEnvVars["LINEAR_TEAM_ID"] ?? null,
        notion_api_key: finalEnvVars["NOTION_API_KEY"] ?? null,
        notion_database_id: finalEnvVars["NOTION_DATABASE_ID"] ?? null,
        hook_ids: state.agents.selectedHooks,
      },
    );
    spinner.succeed(`프로젝트 생성 완료: ${finalizeResult.project_name}`);
  } catch (err) {
    spinner.fail("프로젝트 생성 실패");
    throw err;
  }

  // ── ZIP 다운로드 & 압축 해제 ─────────────────────────────────────────────
  const downloadSpinner = ora("ZIP을 다운로드하고 있습니다...").start();
  let projectDir: string;
  try {
    projectDir = await downloadAndExtract(
      finalizeResult.project_id,
      finalEnvVars,
      finalizeResult.project_name,
    );
    downloadSpinner.succeed(`압축 해제 완료: ${projectDir}`);
  } catch (err) {
    downloadSpinner.fail("ZIP 다운로드 또는 압축 해제 실패");
    throw err;
  }

  // ── 완료 메시지 ────────────────────────────────────────────────────────────
  console.log();
  console.log(chalk.bold.green("🎉 ClickEye 솔루션이 준비되었습니다!\n"));
  console.log(`   프로젝트 위치: ${chalk.cyan(projectDir)}`);
  if (finalizeResult.initial_task_url) {
    console.log(`   Linear 이슈:   ${chalk.dim(finalizeResult.initial_task_url)}`);
  }
  console.log();
  console.log(chalk.dim("  다음 단계:"));
  console.log(chalk.dim(`  1. cd ${projectDir}`));
  console.log(chalk.dim("  2. cat README.md  (또는 cat .claude/README.md)"));
  console.log(chalk.dim("  3. bash start.sh  (환경 설정 후 실행)"));
  console.log();

  // 완료된 세션 파일 정리
  if (state.sessionId) {
    await deleteSession(state.sessionId).catch(() => undefined);
  }

  return {
    ...state,
    currentStep: 12,
  };
}
