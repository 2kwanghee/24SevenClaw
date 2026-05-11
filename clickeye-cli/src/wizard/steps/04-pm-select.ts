import inquirer from "inquirer";
import chalk from "chalk";
import { apiClient } from "../../api/client.js";
import type { WizardState } from "../state.js";

export async function step04PMSelect(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n✋ Step 4 — PM 선택\n"));

  const { recommendedPMs } = state.pm;

  if (recommendedPMs.length === 0) {
    throw new Error("추천된 PM이 없습니다. Step 3을 다시 실행해 주세요.");
  }

  const choices = recommendedPMs.map((pm) => {
    const score = Math.round(pm.matchScore * 100);
    const meta = pm.title ?? pm.domain ?? "";
    return {
      name:
        `${chalk.cyan(pm.name)} ` +
        chalk.dim(`[${score}% 매칭]`) +
        (meta ? ` — ${meta}` : ""),
      value: pm.pmId,
      short: pm.name,
    };
  });

  const { selectedPmId } = await inquirer.prompt<{ selectedPmId: string }>([
    {
      type: "list",
      name: "selectedPmId",
      message: "함께할 PM을 선택해 주세요:",
      choices,
    },
  ]);

  const selected = recommendedPMs.find((p) => p.pmId === selectedPmId);
  if (!selected) throw new Error(`선택된 PM을 찾을 수 없습니다: ${selectedPmId}`);
  console.log(chalk.bold(`\n✅ 선택됨: ${selected.name}`));
  if (selected.title) console.log(chalk.dim(`   ${selected.title}`));
  if (selected.domain) console.log(chalk.dim(`   전문 도메인: ${selected.domain}`));
  console.log(chalk.dim(`   추천 이유: ${selected.reasoning}`));
  console.log();

  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    selected_pm_id: selectedPmId,
    current_step: 5,
  });

  return {
    ...state,
    currentStep: 5,
    pm: {
      ...state.pm,
      selectedPmProfileId: selectedPmId,
    },
  };
}
