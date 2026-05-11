import chalk from "chalk";
import ora from "ora";
import { apiClient } from "../../api/client.js";
import type { WizardState, PrototypeItem } from "../state.js";

const POLL_INTERVAL_MS = 3_000;
const POLL_TIMEOUT_MS = 5 * 60 * 1_000;

export interface GenerationOptions {
  pollIntervalMs?: number;
}

interface ApiPrototype {
  id: string;
  variant_index: number;
  title: string;
  description: string | null;
  is_recommended: boolean;
  pros: string[];
  cons: string[];
}

interface PrototypeListResponse {
  items: ApiPrototype[];
  total: number;
}

interface StatusResponse {
  status: string;
}

export async function step01Generation(
  state: WizardState,
  options: GenerationOptions = {},
): Promise<WizardState> {
  const pollIntervalMs = options.pollIntervalMs ?? POLL_INTERVAL_MS;
  if (!state.sessionId) throw new Error("세션 ID가 없습니다");

  console.log(chalk.bold("\n🤖 Step 1 — 프로토타입 생성\n"));

  const spinner = ora("프로토타입 생성 요청 중...").start();

  try {
    await apiClient.post(
      `/api/v1/prototype-sessions/${state.sessionId}/prototypes/generate`,
    );

    spinner.text = "AI가 프로토타입을 생성하고 있습니다...";

    let done = false;
    const deadline = Date.now() + POLL_TIMEOUT_MS;

    while (Date.now() < deadline) {
      const { status } = await apiClient.get<StatusResponse>(
        `/api/v1/prototype-sessions/${state.sessionId}/status`,
      );

      if (status === "completed") {
        done = true;
        break;
      }

      if (status === "failed") {
        throw new Error("프로토타입 생성에 실패했습니다. 다시 시도해 주세요.");
      }

      await new Promise<void>((r) => setTimeout(r, pollIntervalMs));
    }

    if (!done) {
      throw new Error("프로토타입 생성 시간이 초과되었습니다.");
    }

    const list = await apiClient.get<PrototypeListResponse>(
      `/api/v1/prototype-sessions/${state.sessionId}/prototypes`,
    );

    spinner.succeed("프로토타입 생성 완료!");

    const prototypes: PrototypeItem[] = list.items.map((p) => ({
      id: p.id,
      variantIndex: p.variant_index,
      title: p.title,
      description: p.description,
      isRecommended: p.is_recommended,
      pros: p.pros,
      cons: p.cons,
    }));

    return {
      ...state,
      currentStep: 2,
      prototypes: {
        ...state.prototypes,
        prototypes,
      },
    };
  } catch (err) {
    if (!spinner.isSpinning) throw err; // 이미 succeed/fail 처리된 경우
    spinner.fail("프로토타입 생성 오류");
    throw err;
  }
}
