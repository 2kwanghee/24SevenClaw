import chalk from "chalk";
import inquirer from "inquirer";
import { INITIAL_WIZARD_STATE, type WizardState } from "../wizard/state.js";
import { saveSession, loadSession, listSessions } from "../wizard/session.js";
import { step00Company } from "../wizard/steps/00-company.js";
import { step01Generation } from "../wizard/steps/01-generation.js";
import { step02PrototypeSelect } from "../wizard/steps/02-prototype-select.js";
import { step03PMRecommend } from "../wizard/steps/03-pm-recommend.js";
import { step04PMSelect } from "../wizard/steps/04-pm-select.js";
import { step05PMComposition } from "../wizard/steps/05-pm-composition.js";
import { step06Agents } from "../wizard/steps/06-agents.js";
import { step07Platform } from "../wizard/steps/07-platform.js";
import { step08Os } from "../wizard/steps/08-os.js";
import { step09Env } from "../wizard/steps/09-env.js";
import { step10Roi } from "../wizard/steps/10-roi.js";
import { step11Confirm } from "../wizard/steps/11-confirm.js";
import { AuthRequiredError } from "../api/client.js";

interface InitFlags {
  resume?: string;
}

type StepRunner = (state: WizardState) => Promise<WizardState>;

const STEP_RUNNERS: StepRunner[] = [
  step00Company,        // 0
  step01Generation,     // 1
  step02PrototypeSelect, // 2
  step03PMRecommend,    // 3
  step04PMSelect,       // 4
  step05PMComposition,  // 5
  step06Agents,         // 6
  step07Platform,       // 7
  step08Os,             // 8
  step09Env,            // 9
  step10Roi,            // 10
  step11Confirm,        // 11
];

export async function initCommand(flags: InitFlags): Promise<void> {
  let state: WizardState;

  if (flags.resume) {
    let loaded: WizardState | null;
    try {
      loaded = await loadSession(flags.resume);
    } catch (err) {
      console.error(chalk.red(`\n❌ ${String(err)}\n`));
      process.exit(1);
    }
    if (!loaded) {
      console.error(
        chalk.red(`\n❌ 세션 '${flags.resume}'을 찾을 수 없습니다.\n`),
      );
      process.exit(1);
    }
    console.log(
      chalk.cyan(
        `\n🔄 세션 재개: Step ${loaded.currentStep}부터 시작합니다.\n`,
      ),
    );
    state = loaded;
  } else {
    // 저장된 세션이 있으면 목록 표시 후 선택
    const sessions = await listSessions();
    if (sessions.length > 0) {
      const choices = [
        ...sessions.map((s) => {
          const name = s.companyName ?? "(회사명 미입력)";
          const date = s.savedAt.toLocaleString("ko-KR", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          });
          return {
            name: `[Step ${s.currentStep}/${STEP_RUNNERS.length}] ${chalk.cyan(name)} — ${chalk.dim(date)}`,
            value: s.sessionId,
          };
        }),
        { name: chalk.bold("새로 시작"), value: null as string | null },
      ];

      const { sessionChoice } = await inquirer.prompt<{ sessionChoice: string | null }>([
        {
          type: "list",
          name: "sessionChoice",
          message: "💾 저장된 진행 중 세션이 있습니다. 어떻게 할까요?",
          choices,
        },
      ]);

      if (sessionChoice) {
        let loaded: WizardState | null;
        try {
          loaded = await loadSession(sessionChoice);
        } catch (err) {
          console.error(chalk.red(`\n❌ ${String(err)}\n`));
          process.exit(1);
        }
        if (loaded) {
          console.log(chalk.cyan(`\n🔄 세션 재개: Step ${loaded.currentStep}부터 시작합니다.\n`));
          state = loaded;
        } else {
          console.log(chalk.yellow("\n⚠️  세션을 찾을 수 없습니다. 새로 시작합니다.\n"));
          state = structuredClone(INITIAL_WIZARD_STATE);
        }
      } else {
        state = structuredClone(INITIAL_WIZARD_STATE);
      }
    } else {
      state = structuredClone(INITIAL_WIZARD_STATE);
    }

    if (state.currentStep === 0) {
      console.log(chalk.bold("\n🚀 ClickEye AI 솔루션 위저드\n"));
    }
    console.log(
      chalk.dim(
        "Ctrl+C로 중단하면 자동 저장됩니다. `ce init`으로 재개할 수 있습니다.\n",
      ),
    );
  }

  process.once("SIGINT", async () => {
    if (state.sessionId) {
      await saveSession(state);
      console.log(
        chalk.yellow(
          `\n⏸  세션 저장됨. 재개하려면:\n  ce init --resume ${state.sessionId}\n`,
        ),
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
      console.log(chalk.bold.green("\n✅ 위저드 완료!\n"));
    }
  } catch (err) {
    if (err instanceof AuthRequiredError) {
      console.error(chalk.red(`\n❌ ${err.message}\n`));
      process.exit(1);
    }
    console.error(chalk.red(`\n❌ 오류 발생: ${String(err)}\n`));
    if (state.sessionId) {
      await saveSession(state);
      console.log(
        chalk.dim(`세션 저장됨. 재개: ce init --resume ${state.sessionId}`),
      );
    }
    process.exit(1);
  }
}
