import inquirer from "inquirer";
import chalk from "chalk";
import { apiClient } from "../../api/client.js";
import type { WizardState } from "../state.js";

interface PMCompositionItem {
  id: string;
  component_type: string;
  component_slug: string;
  component_name: string;
  config: Record<string, unknown>;
  is_required: boolean;
  display_order: number;
}

interface PMCompositionGrouped {
  agents: PMCompositionItem[];
  skills: PMCompositionItem[];
  hooks: PMCompositionItem[];
  mcp_servers: PMCompositionItem[];
  plugins: PMCompositionItem[];
}

function renderSection(emoji: string, title: string, items: PMCompositionItem[]): void {
  if (items.length === 0) return;
  const sorted = [...items].sort((a, b) => a.display_order - b.display_order);
  console.log(chalk.bold(`  ${emoji} ${title} (${sorted.length}개)`));
  for (const item of sorted) {
    const badge = item.is_required
      ? chalk.red("[필수]")
      : chalk.dim("[선택]");
    console.log(
      `    ${badge} ${chalk.cyan(item.component_name)} ` +
        chalk.dim(`(${item.component_slug})`),
    );
    const rawDesc = item.config["description"];
    const desc = typeof rawDesc === "string" ? rawDesc : undefined;
    if (desc) console.log(`         ${chalk.dim(desc)}`);
  }
  console.log();
}

export async function step05PMComposition(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");
  if (!state.pm.selectedPmProfileId) throw new Error("선택된 PM이 없습니다");

  console.log(chalk.bold("\n🧩 Step 5 — PM 구성 확인\n"));

  const composition = await apiClient.get<PMCompositionGrouped>(
    `/api/v1/pm-profiles/${state.pm.selectedPmProfileId}/composition`,
  );

  const selectedPM = state.pm.recommendedPMs.find(
    (p) => p.pmId === state.pm.selectedPmProfileId,
  );

  console.log(
    chalk.bold(`${selectedPM?.name ?? "선택된 PM"}의 기본 구성 스택:\n`),
  );

  renderSection("🤖", "에이전트", composition.agents);
  renderSection("🔧", "스킬", composition.skills);
  renderSection("🪝", "훅", composition.hooks);
  renderSection("🌐", "MCP 서버", composition.mcp_servers);
  renderSection("🔌", "플러그인", composition.plugins);

  const { confirmed } = await inquirer.prompt<{ confirmed: boolean }>([
    {
      type: "confirm",
      name: "confirmed",
      message: "이 구성으로 계속하시겠습니까?",
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

  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    current_step: 6,
  });

  return {
    ...state,
    currentStep: 6,
  };
}
