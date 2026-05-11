import chalk from "chalk";
import ora from "ora";
import { apiClient } from "../../api/client.js";
import type { WizardState, PMRecommendItem } from "../state.js";

interface ApiPMItem {
  pm_id: string;
  name: string;
  slug: string;
  title: string | null;
  domain: string | null;
  match_score: number;
  reasoning: string;
}

interface RecommendPMsResponse {
  items: ApiPMItem[];
}

export async function step03PMRecommend(state: WizardState): Promise<WizardState> {
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n👔 Step 3 — PM 추천\n"));

  const spinner = ora("AI가 최적의 PM을 추천하고 있습니다...").start();

  try {
    const res = await apiClient.post<RecommendPMsResponse>(
      `/api/v1/prototype-sessions/${state.sessionId}/recommend-pms`,
    );

    spinner.succeed(`${res.items.length}명의 PM 추천 완료!`);

    const recommendedPMs: PMRecommendItem[] = res.items.map((p) => ({
      pmId: p.pm_id,
      name: p.name,
      slug: p.slug,
      title: p.title,
      domain: p.domain,
      matchScore: p.match_score,
      reasoning: p.reasoning,
    }));

    console.log(chalk.bold("\n📋 추천 PM 목록:\n"));
    recommendedPMs.forEach((pm, i) => {
      const score = Math.round(pm.matchScore * 100);
      console.log(
        `  ${chalk.bold(String(i + 1))}. ${chalk.cyan(pm.name)} ` +
          chalk.dim(`(${pm.title ?? pm.domain ?? "PM"})`) +
          ` — 매칭 ${chalk.green(`${score}%`)}`,
      );
      const preview = pm.reasoning.length > 80
        ? `${pm.reasoning.slice(0, 80)}...`
        : pm.reasoning;
      console.log(`     ${chalk.dim(preview)}`);
    });
    console.log();

    return {
      ...state,
      currentStep: 4,
      pm: {
        ...state.pm,
        recommendedPMs,
      },
    };
  } catch (err) {
    spinner.fail("PM 추천 실패");
    throw err;
  }
}
