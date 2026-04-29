import inquirer from "inquirer";
import type { WorkflowId, WorkflowSelection } from "../types.js";
import catalogSkills from "../catalog/skills.json" with { type: "json" };

export async function promptWorkflowSelection(): Promise<WorkflowSelection> {
  const answers = await inquirer.prompt([
    {
      type: "checkbox",
      name: "workflows",
      message: "적용할 워크플로우를 선택하세요 (하네스 Gate 권장):",
      choices: catalogSkills.map((s) => ({
        name: `${s.name} — ${s.description}`,
        value: s.id,
        checked: s.id === "harness-gate" || s.id === "tdd",
      })),
    },
  ]);

  return { workflows: answers.workflows as WorkflowId[] };
}

/** --yes 플래그 시 기본값 */
export function defaultWorkflowSelection(): WorkflowSelection {
  return {
    workflows: ["tdd", "harness-gate"],
  };
}
