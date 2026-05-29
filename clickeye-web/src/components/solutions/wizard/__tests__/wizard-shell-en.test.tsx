/**
 * 위저드 셸/프리뷰 — 영어(en) 로케일 렌더 스모크 테스트
 *
 * 목적: 영어 모드에서 셸/프리뷰가 한글이 아닌 영어로 렌더되고,
 * ICU 보간({label} 등)이 런타임에 정상 동작하는지 검증한다.
 * (한글 로케일 검증은 solution-wizard-layout.test.tsx 가 담당)
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { act } from "react";
import { NextIntlClientProvider } from "next-intl";

import enMessages from "../../../../../messages/en.json";
import { SolutionWizardLayout } from "../solution-wizard-layout";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({}),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

function renderEn() {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <SolutionWizardLayout canProceed>
        <div>step content</div>
      </SolutionWizardLayout>
    </NextIntlClientProvider>,
  );
}

describe("Wizard shell — English locale", () => {
  beforeEach(() => {
    act(() => useSolutionWizardStore.getState().reset());
  });

  it("헤더가 영어로 렌더된다", () => {
    renderEn();
    expect(
      screen.getByRole("heading", { name: "New solution", level: 1 }),
    ).toBeInTheDocument();
  });

  it("첫 스텝 제목이 영어로 렌더된다", () => {
    renderEn();
    expect(
      screen.getByRole("heading", { name: "Company info" }),
    ).toBeInTheDocument();
  });

  it("라이브 프리뷰 패널 제목이 영어로 렌더된다", () => {
    renderEn();
    expect(screen.getAllByText("Live preview").length).toBeGreaterThan(0);
  });

  it("다음 버튼 aria-label 의 ICU 보간({label})이 영어로 동작한다", () => {
    renderEn();
    // nextAria: "Go to next step ({label})" + steps.generation.label = "Generation"
    expect(
      screen.getByRole("button", { name: "Go to next step (Generation)" }),
    ).toBeInTheDocument();
  });
});
