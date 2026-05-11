import inquirer from "inquirer";
import chalk from "chalk";
import { fetchPlatforms } from "../../api/catalog.js";
import type { WizardState } from "../state.js";

export async function step07Platform(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n🖥️  Step 7 — 플랫폼 선택\n"));

  const platforms = await fetchPlatforms();

  if (platforms.length === 0) {
    throw new Error("플랫폼 카탈로그가 비어 있습니다. 잠시 후 다시 시도해 주세요.");
  }

  const { platformId } = await inquirer.prompt<{ platformId: string }>([
    {
      type: "list",
      name: "platformId",
      message: "배포 플랫폼을 선택해 주세요:",
      choices: platforms.map((p) => ({
        name: p.label,
        value: p.id,
      })),
    },
  ]);

  const selected = platforms.find((p) => p.id === platformId);
  console.log(chalk.bold(`\n✅ 선택됨: ${selected?.label ?? platformId}\n`));

  return {
    ...state,
    currentStep: 8,
    platform: { platformId },
  };
}
