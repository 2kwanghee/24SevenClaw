import inquirer from "inquirer";
import type { AgentId, AgentSelection } from "../types.js";
import catalogAgents from "../catalog/agents.json" with { type: "json" };

export async function promptAgentSelection(): Promise<AgentSelection> {
  const optionalAgents = catalogAgents.filter((a) => !a.required);

  const answers = await inquirer.prompt([
    {
      type: "checkbox",
      name: "agents",
      message: "고용할 에이전트를 선택하세요 (하네스 엔지니어는 필수 포함):",
      choices: optionalAgents.map((a) => ({
        name: `${a.name} — ${a.description}`,
        value: a.id,
        checked: a.id === "backend" || a.id === "frontend",
      })),
    },
  ]);

  // 하네스 엔지니어는 항상 포함
  const agents: AgentId[] = [...answers.agents, "harness"];
  return { agents };
}

/** --yes 플래그 시 기본값 */
export function defaultAgentSelection(): AgentSelection {
  return {
    agents: ["backend", "frontend", "harness"],
  };
}
