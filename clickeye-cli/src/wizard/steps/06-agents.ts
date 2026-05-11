import inquirer from "inquirer";
import chalk from "chalk";
import { apiClient } from "../../api/client.js";
import { fetchAgents, fetchSkills, fetchHooks } from "../../api/catalog.js";
import type { WizardState } from "../state.js";

interface RecommendComponentsResponse {
  agents: string[];
  skills: string[];
  excluded_agents: string[];
  reasoning: string | null;
}

function isRecommended(idOrSlug: string, recommended: string[]): boolean {
  return recommended.includes(idOrSlug);
}

export async function step06Agents(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n🤖 Step 6 — 에이전트 & 스킬 구성\n"));

  // 추천 컴포넌트 조회 (실패해도 계속)
  let recommended: RecommendComponentsResponse = {
    agents: [],
    skills: [],
    excluded_agents: [],
    reasoning: null,
  };
  try {
    recommended = await apiClient.get<RecommendComponentsResponse>(
      `/api/v1/prototype-sessions/${state.sessionId}/recommend-components`,
    );
    if (recommended.reasoning) {
      console.log(
        chalk.dim(
          `💡 추천 근거: ${recommended.reasoning.slice(0, 100)}${recommended.reasoning.length > 100 ? "..." : ""}\n`,
        ),
      );
    }
  } catch {
    // 추천 실패해도 계속 진행
  }

  // 카탈로그 병렬 조회
  const [catalogAgents, catalogSkills, catalogHooks] = await Promise.all([
    fetchAgents(),
    fetchSkills(),
    fetchHooks(),
  ]);

  // ── 에이전트 선택 ─────────────────────────────────────────────────────────
  const eligibleAgents = catalogAgents.filter(
    (a) => !isRecommended(a.id, recommended.excluded_agents) &&
           !isRecommended(a.slug, recommended.excluded_agents),
  );

  if (eligibleAgents.length === 0) {
    throw new Error("에이전트 카탈로그가 비어 있습니다. 잠시 후 다시 시도해 주세요.");
  }

  let selectedAgents: string[] = [];
  while (selectedAgents.length === 0) {
    const agentChoices = eligibleAgents.map((a) => ({
      name: `${chalk.cyan(a.slug.padEnd(22))} ${a.label}`,
      value: a.id,
      checked: isRecommended(a.id, recommended.agents) ||
               isRecommended(a.slug, recommended.agents),
    }));

    const answer = await inquirer.prompt<{ agents: string[] }>([
      {
        type: "checkbox",
        name: "agents",
        message: "에이전트를 선택해 주세요 (최소 1개):",
        choices: agentChoices,
      },
    ]);

    if (answer.agents.length === 0) {
      console.log(chalk.red("  ❌ 에이전트를 최소 1개 선택해야 합니다.\n"));
    } else {
      selectedAgents = answer.agents;
    }
  }

  // ── 스킬 분류 ─────────────────────────────────────────────────────────────
  const ticketSourceSkills = catalogSkills.filter(
    (s) => s.category === "ticket_source",
  );
  const otherSkills = catalogSkills.filter(
    (s) => s.category !== "ticket_source",
  );

  const selectedSkills: string[] = [];

  // ticket_source (필수 1개, XOR)
  if (ticketSourceSkills.length > 0) {
    console.log(chalk.bold("\n🎫 티켓 소스 선택 (필수 — 1개):"));
    const preSelected = ticketSourceSkills.find(
      (s) =>
        isRecommended(s.id, recommended.skills) ||
        isRecommended(s.slug, recommended.skills),
    );

    const { ticketSource } = await inquirer.prompt<{ ticketSource: string }>([
      {
        type: "list",
        name: "ticketSource",
        message: "티켓 소스를 선택해 주세요:",
        choices: ticketSourceSkills.map((s) => ({
          name: `${chalk.cyan(s.slug.padEnd(20))} ${s.label}`,
          value: s.id,
        })),
        default: preSelected?.id ?? ticketSourceSkills[0]?.id,
      },
    ]);
    selectedSkills.push(ticketSource);
  }

  // 추가 스킬 (선택)
  if (otherSkills.length > 0) {
    console.log(chalk.bold("\n🔧 추가 스킬 선택 (선택):"));
    const skillChoices = otherSkills.map((s) => ({
      name: `${chalk.cyan(s.slug.padEnd(22))} ${s.label}`,
      value: s.id,
      checked: isRecommended(s.id, recommended.skills) ||
               isRecommended(s.slug, recommended.skills),
    }));

    const { additionalSkills } = await inquirer.prompt<{
      additionalSkills: string[];
    }>([
      {
        type: "checkbox",
        name: "additionalSkills",
        message: "추가 스킬을 선택해 주세요:",
        choices: skillChoices,
      },
    ]);
    selectedSkills.push(...additionalSkills);
  }

  // ── 훅 선택 (선택) ────────────────────────────────────────────────────────
  let selectedHooks: string[] = [];
  if (catalogHooks.length > 0) {
    const { hooks } = await inquirer.prompt<{ hooks: string[] }>([
      {
        type: "checkbox",
        name: "hooks",
        message: "훅을 선택해 주세요 (선택):",
        choices: catalogHooks.map((h) => ({
          name: `${chalk.cyan(h.slug.padEnd(22))} ${h.label}`,
          value: h.id,
          checked: false,
        })),
      },
    ]);
    selectedHooks = hooks;
  }

  await apiClient.patch(`/api/v1/prototype-sessions/${state.sessionId}`, {
    current_step: 7,
  });

  return {
    ...state,
    currentStep: 7,
    agents: {
      selectedAgents,
      selectedSkills,
      selectedHooks,
    },
  };
}
