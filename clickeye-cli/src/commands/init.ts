import chalk from "chalk";
import { INITIAL_WIZARD_STATE, type WizardState } from "../wizard/state.js";
import { saveSession, loadSession } from "../wizard/session.js";
import { step00Company } from "../wizard/steps/00-company.js";
import { step01Generation } from "../wizard/steps/01-generation.js";
import { step02PrototypeSelect } from "../wizard/steps/02-prototype-select.js";
import { step03PMRecommend } from "../wizard/steps/03-pm-recommend.js";
import { step04PMSelect } from "../wizard/steps/04-pm-select.js";
import { step05PMComposition } from "../wizard/steps/05-pm-composition.js";
import { step06Agents } from "../wizard/steps/06-agents.js";
import { AuthRequiredError } from "../api/client.js";

interface InitFlags {
  resume?: string;
}

type StepRunner = (state: WizardState) => Promise<WizardState>;

// Phase 5~6에서 나머지 step runner가 추가됩니다
const STEP_RUNNERS: StepRunner[] = [
  step00Company,        // 0
  step01Generation,     // 1
  step02PrototypeSelect, // 2
  step03PMRecommend,    // 3
  step04PMSelect,       // 4
  step05PMComposition,  // 5
  step06Agents,         // 6
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
    state = structuredClone(INITIAL_WIZARD_STATE);
    console.log(chalk.bold("\n🚀 ClickEye AI 솔루션 위저드\n"));
    console.log(
      chalk.dim(
        "Ctrl+C로 중단 후 `ce init --resume <sessionId>`로 재개할 수 있습니다.\n",
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
      console.log(
        chalk.bold.green(
          "\n✅ 위저드 완료!\n   (Phase 4~6에서 finalize 및 ZIP 다운로드 구현 예정)\n",
        ),
      );
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
