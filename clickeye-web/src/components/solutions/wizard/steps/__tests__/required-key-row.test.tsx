/**
 * RequiredKeyRow 컴포넌트 — input sanitize 회귀 방지 테스트.
 *
 * 사용자 보고: 한글을 입력하면 state 에 한글이 들어가 fetch 가 실패.
 * 직전 변경: input onChange 에서 sanitizeIntegrationInput 으로 비-ASCII 즉시 제거.
 * 본 테스트가 실제 React 렌더링 + paste 이벤트 경로로 동작을 결정적 확인한다.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import koMessages from "../../../../../../messages/ko.json";
import { RequiredKeyRow } from "../step-solution-env";

const CONFIG = {
  key: "LINEAR_API_KEY",
  label: "Linear API Key",
  description: "Linear 이슈 트래킹 인증 키",
};

function renderRow(onChange = vi.fn()) {
  const utils = render(
    <NextIntlClientProvider locale="ko" messages={koMessages}>
      <RequiredKeyRow config={CONFIG} value="" onChange={onChange} />
    </NextIntlClientProvider>,
  );
  return { onChange, ...utils };
}

async function openEditor(user: ReturnType<typeof userEvent.setup>) {
  // 수정/입력 버튼 클릭 → input 노출
  const openButton = await screen.findByRole("button", { name: /입력/ });
  await user.click(openButton);
  return screen.getByLabelText(/Linear API Key 입력/);
}

describe("RequiredKeyRow — 한글 sanitize 동작", () => {
  it("순수 한글 paste → input value 가 빈 문자열로 유지되고 amber 안내가 표시된다", async () => {
    const user = userEvent.setup();
    renderRow();
    const input = await openEditor(user);

    await user.click(input);
    await user.paste("한글입력");

    expect(input).toHaveValue("");
    expect(
      screen.getByText(/비-ASCII 문자는 자동 제거/),
    ).toBeInTheDocument();
  });

  it("한글 + ASCII 혼합 paste → ASCII 만 남고 안내 노출", async () => {
    const user = userEvent.setup();
    renderRow();
    const input = await openEditor(user);

    await user.click(input);
    await user.paste("lin한_api_abc글123");

    expect(input).toHaveValue("lin_api_abc123");
    expect(
      screen.getByText(/비-ASCII 문자는 자동 제거/),
    ).toBeInTheDocument();
  });

  it("순수 ASCII 입력은 그대로 통과하고 안내가 안 보인다", async () => {
    const user = userEvent.setup();
    renderRow();
    const input = await openEditor(user);

    await user.click(input);
    await user.type(input, "lin_api_abcXYZ_123");

    expect(input).toHaveValue("lin_api_abcXYZ_123");
    expect(
      screen.queryByText(/비-ASCII 문자는 자동 제거/),
    ).not.toBeInTheDocument();
  });

  it("저장 클릭 → onChange 콜백에 sanitize 된 값이 전달된다", async () => {
    const user = userEvent.setup();
    const { onChange } = renderRow();
    const input = await openEditor(user);

    await user.click(input);
    await user.paste("lin한_api_abc"); // 한글 포함

    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(onChange).toHaveBeenCalledWith("LINEAR_API_KEY", "lin_api_abc");
  });

  it("이모지 paste → 모두 제거되고 안내 노출", async () => {
    const user = userEvent.setup();
    renderRow();
    const input = await openEditor(user);

    await user.click(input);
    await user.paste("token🎉end");

    expect(input).toHaveValue("tokenend");
    expect(
      screen.getByText(/비-ASCII 문자는 자동 제거/),
    ).toBeInTheDocument();
  });
});
