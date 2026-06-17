/**
 * StepPMRecommendation — recommend-pms(LLM POST) 중복 호출 방지 회귀 테스트
 *
 * 목적(중복 GPT 호출 점검):
 * - React 18 StrictMode 이중 마운트에도 recommend-pms는 정확히 1회만 호출되어야 한다.
 * - 토큰 갱신(SessionProvider refetch)으로 인한 재렌더에도 동일 sessionId면 추가 호출이 없어야 한다.
 * - 단일 호출의 결과는 보존되어 setStep3Done(true)가 발화해야 한다(StrictMode cleanup이 결과를 버리지 않음).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { act, StrictMode } from "react";
import { NextIntlClientProvider } from "next-intl";

import { StepPMRecommendation } from "../step-pm-recommendation";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import messages from "../../../../../../messages/ko.json";

/* -- 모킹 -- */

let currentToken = "tok-1";
vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { accessToken: currentToken },
    status: "authenticated",
  }),
}));

const recommendPMs = vi.fn();
vi.mock("@/lib/api-client", () => ({
  prototypeSessions: {
    recommendPMs: (...args: unknown[]) => recommendPMs(...args),
  },
  ApiClientError: class ApiClientError extends Error {
    status: number;
    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
    }
  },
}));

/* -- 헬퍼 -- */

function tree() {
  return (
    <StrictMode>
      <NextIntlClientProvider locale="ko" messages={messages}>
        <StepPMRecommendation />
      </NextIntlClientProvider>
    </StrictMode>
  );
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/* -- 테스트 -- */

describe("StepPMRecommendation — recommend-pms 중복 호출 방지", () => {
  beforeEach(() => {
    currentToken = "tok-1";
    recommendPMs.mockReset();
    recommendPMs.mockResolvedValue({
      items: [
        {
          pm_id: "p1",
          name: "PM A",
          slug: "pm-a",
          avatar_url: null,
          title: "",
          domain: "product",
          match_score: 90,
          reasoning: "적합",
          dimension_scores: {},
          match_reasons: [],
        },
      ],
    });
    act(() => {
      useSolutionWizardStore.getState().reset();
      useSolutionWizardStore.getState().setSessionId("sess-1");
    });
  });

  it("StrictMode 이중 마운트에도 recommend-pms를 정확히 1회만 호출하고 결과를 보존한다", async () => {
    render(tree());

    await waitFor(() => expect(recommendPMs).toHaveBeenCalledTimes(1));
    // 결과 보존: 완료 플래그 발화 (StrictMode cleanup이 in-flight 결과를 버리지 않음)
    await waitFor(() =>
      expect(useSolutionWizardStore.getState().step3Done).toBe(true),
    );
    // 안정화 후에도 1회 유지
    await sleep(60);
    expect(recommendPMs).toHaveBeenCalledTimes(1);
  });

  it("토큰 변경 재렌더(동일 sessionId)에도 추가 호출이 없다", async () => {
    const { rerender } = render(tree());
    await waitFor(() => expect(recommendPMs).toHaveBeenCalledTimes(1));

    // SessionProvider refetch로 accessToken이 바뀌는 상황 모사 → 재렌더
    currentToken = "tok-2";
    act(() => {
      rerender(tree());
    });

    await sleep(60);
    expect(recommendPMs).toHaveBeenCalledTimes(1);
  });
});
