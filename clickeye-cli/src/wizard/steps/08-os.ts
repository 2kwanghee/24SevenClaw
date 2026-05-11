import inquirer from "inquirer";
import chalk from "chalk";
import type { WizardState } from "../state.js";

const WSL2_OS_ID = "wsl2";

export async function step08Os(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n🐧 Step 8 — 실행 환경 선택\n"));
  console.log(
    chalk.dim(
      "현재 지원하는 실행 환경은 WSL2(Windows Subsystem for Linux 2)입니다.\n" +
      "macOS/Linux 네이티브 지원은 추후 추가될 예정입니다.\n",
    ),
  );

  const { confirmed } = await inquirer.prompt<{ confirmed: boolean }>([
    {
      type: "confirm",
      name: "confirmed",
      message: "WSL2 환경으로 계속하시겠습니까?",
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

  return {
    ...state,
    currentStep: 9,
    os: { osId: WSL2_OS_ID },
  };
}
