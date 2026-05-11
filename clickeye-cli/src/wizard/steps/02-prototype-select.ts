import inquirer from "inquirer";
import chalk from "chalk";
import { apiClient } from "../../api/client.js";
import type { WizardState } from "../state.js";

export async function step02PrototypeSelect(
  state: WizardState,
): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n🎨 Step 2 — 프로토타입 선택\n"));

  const { prototypes } = state.prototypes;

  if (prototypes.length === 0) {
    throw new Error("선택할 프로토타입이 없습니다.");
  }

  const choices = prototypes.map((p) => ({
    name:
      `${p.isRecommended ? "⭐ " : "  "}${p.title}` +
      (p.description ? chalk.dim(` — ${p.description.slice(0, 60)}`) : ""),
    value: p.id,
    short: p.title,
  }));

  const { selectedId } = await inquirer.prompt<{ selectedId: string }>([
    {
      type: "list",
      name: "selectedId",
      message: "사용할 프로토타입을 선택해 주세요:",
      choices,
      default: prototypes.find((p) => p.isRecommended)?.id,
    },
  ]);

  const selected = prototypes.find((p) => p.id === selectedId)!;
  console.log(chalk.bold(`\n✅ 선택됨: ${selected.title}`));
  if (selected.pros.length > 0) {
    console.log(chalk.green("  장점:"));
    selected.pros.forEach((p) => console.log(`  • ${p}`));
  }
  if (selected.cons.length > 0) {
    console.log(chalk.yellow("  단점:"));
    selected.cons.forEach((c) => console.log(`  • ${c}`));
  }
  console.log();

  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    selected_prototype_id: selectedId,
    current_step: 3,
  });

  return {
    ...state,
    currentStep: 3,
    prototypes: {
      ...state.prototypes,
      selectedPrototypeId: selectedId,
    },
  };
}
