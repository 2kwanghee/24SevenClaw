import inquirer from "inquirer";
import chalk from "chalk";
import ora from "ora";
import { apiClient } from "../../api/client.js";
import type { WizardState, RoiCalculateResponse } from "../state.js";


function formatKRW(amount: number): string {
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency: "KRW",
    maximumFractionDigits: 0,
  }).format(amount);
}

export async function step10Roi(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n📊 Step 10 — ROI 분석\n"));

  const { complexity } = await inquirer.prompt<{
    complexity: "low" | "medium" | "high";
  }>([
    {
      type: "list",
      name: "complexity",
      message: "프로젝트 복잡도를 선택해 주세요:",
      choices: [
        { name: "낮음 (Low)   — 단순 반복 업무 자동화", value: "low" },
        { name: "중간 (Medium) — 복합 워크플로 자동화", value: "medium" },
        { name: "높음 (High)  — 대규모 멀티 에이전트 시스템", value: "high" },
      ],
      default: "medium",
    },
  ]);

  const selectedPrototype = state.prototypes.prototypes.find(
    (p) => p.id === state.prototypes.selectedPrototypeId,
  );
  if (!selectedPrototype) {
    throw new Error(
      "선택된 프로토타입을 찾을 수 없습니다. `ce init --resume` 또는 처음부터 다시 시작해 주세요.",
    );
  }
  const solutionType = selectedPrototype.title;

  const spinner = ora("ROI를 계산하고 있습니다...").start();

  let roi: RoiCalculateResponse;
  try {
    roi = await apiClient.post<RoiCalculateResponse>("/api/v1/roi/calculate", {
      solution_type: solutionType,
      complexity,
      selected_agents_count: state.agents.selectedAgents.length,
      selected_skills_count: state.agents.selectedSkills.length,
      selected_hooks_count: state.agents.selectedHooks.length,
      platform_id: state.platform.platformId,
    });
    spinner.succeed("ROI 계산 완료!");
  } catch (err) {
    spinner.fail("ROI 계산 실패");
    throw err;
  }

  // ── 결과 출력 ─────────────────────────────────────────────────────────────
  const savingsPct = Math.round(roi.savings_ratio * 100);
  console.log();
  console.log(
    chalk.bold("  ROI 분석 결과") +
      chalk.dim(` (공식 버전: ${roi.formula_version})`),
  );
  console.log("  " + "─".repeat(50));
  console.log(
    `  ${chalk.dim("기존 개발 비용:")}  ${chalk.white(formatKRW(roi.baseline_cost))} ` +
      chalk.dim(`(${roi.baseline_days}일)`),
  );
  console.log(
    `  ${chalk.dim("ClickEye 비용:")}   ${chalk.cyan(formatKRW(roi.clickeye_cost))} ` +
      chalk.dim(`(${roi.clickeye_days}일)`),
  );
  console.log(
    `  ${chalk.dim("절감액:")}           ${chalk.green(formatKRW(roi.savings))} ` +
      chalk.bold.green(`(${savingsPct}% 절감)`),
  );

  if (roi.breakdown.length > 0) {
    console.log();
    console.log(chalk.bold("  역할별 공수:"));
    for (const item of roi.breakdown) {
      console.log(
        `    ${chalk.dim(item.label.padEnd(20))} ${String(item.days).padStart(5)}일  ` +
          chalk.dim(formatKRW(item.subtotal)),
      );
    }
  }
  console.log();

  const { confirmed } = await inquirer.prompt<{ confirmed: boolean }>([
    {
      type: "confirm",
      name: "confirmed",
      message: "이 ROI 분석으로 계속하시겠습니까?",
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
    currentStep: 11,
    roi: { result: roi },
  };
}
