/**
 * SolutionWizardLayout — 네비게이션 버튼 테스트
 *
 * 검증 항목:
 * - 첫 번째 스텝에서 이전 버튼 비활성화
 * - canProceed=false 시 다음 버튼 비활성화
 * - 다음 버튼 클릭 시 스텝 이동 또는 onNextStep 호출
 * - 마지막 스텝에서 다음 버튼 클릭 시 onSubmit 호출
 * - isSubmitting=true 시 버튼 비활성화 + 로딩 스피너
 * - 뒤로가기: prevStep 호출
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act } from "react";

import { SolutionWizardLayout } from "../solution-wizard-layout";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { SOLUTION_WIZARD_STEPS } from "@/types/solution-wizard";

/* -- 모킹 -- */

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({}),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

/* -- 헬퍼 -- */

interface RenderOptions {
  onSubmit?: () => void;
  onNextStep?: () => Promise<void>;
  isSubmitting?: boolean;
  canProceed?: boolean;
  nextLabel?: string;
}

function renderLayout({
  onSubmit = vi.fn(),
  onNextStep,
  isSubmitting = false,
  canProceed = true,
  nextLabel,
}: RenderOptions = {}) {
  return render(
    <SolutionWizardLayout
      onSubmit={onSubmit}
      onNextStep={onNextStep}
      isSubmitting={isSubmitting}
      canProceed={canProceed}
      nextLabel={nextLabel}
    >
      <div>스텝 콘텐츠</div>
    </SolutionWizardLayout>
  );
}

// 이전 버튼은 aria-label="이전 단계로 이동"
const PREV_BTN_LABEL = "이전 단계로 이동";
// 마지막 스텝 다음 버튼은 aria-label="프로젝트 생성하기"
const SUBMIT_BTN_LABEL = "프로젝트 생성하기";

/* -- 테스트 -- */

describe("SolutionWizardLayout — 네비게이션", () => {
  beforeEach(() => {
    act(() => useSolutionWizardStore.getState().reset());
  });

  it("Step 0: 이전 버튼이 비활성화됨", () => {
    renderLayout();

    const prevButton = screen.getByRole("button", { name: PREV_BTN_LABEL });
    expect(prevButton).toBeDisabled();
  });

  it("Step 0: canProceed=true 시 다음 버튼 활성화", () => {
    renderLayout({ canProceed: true });

    // 첫 스텝 다음 버튼: aria-label="다음 단계로 이동 (솔루션 생성)"
    const nextLabel = `다음 단계로 이동 (${SOLUTION_WIZARD_STEPS[1].label})`;
    const nextButton = screen.getByRole("button", { name: nextLabel });
    expect(nextButton).not.toBeDisabled();
  });

  it("Step 0: canProceed=false 시 다음 버튼 비활성화", () => {
    renderLayout({ canProceed: false });

    const nextLabel = `다음 단계로 이동 (${SOLUTION_WIZARD_STEPS[1].label})`;
    const nextButton = screen.getByRole("button", { name: nextLabel });
    expect(nextButton).toBeDisabled();
  });

  it("다음 버튼 클릭 시 onNextStep이 제공되면 호출됨", async () => {
    const user = userEvent.setup();
    const onNextStep = vi.fn().mockResolvedValue(undefined);
    renderLayout({ onNextStep, canProceed: true });

    const nextLabel = `다음 단계로 이동 (${SOLUTION_WIZARD_STEPS[1].label})`;
    await user.click(screen.getByRole("button", { name: nextLabel }));

    expect(onNextStep).toHaveBeenCalledOnce();
  });

  it("다음 버튼 클릭 시 onNextStep 미제공이면 내부 nextStep 호출 (currentStep 증가)", async () => {
    const user = userEvent.setup();
    renderLayout({ canProceed: true });

    const nextLabel = `다음 단계로 이동 (${SOLUTION_WIZARD_STEPS[1].label})`;
    await user.click(screen.getByRole("button", { name: nextLabel }));

    expect(useSolutionWizardStore.getState().currentStep).toBe(1);
  });

  it("Step 1 이상에서 이전 버튼 클릭 시 prevStep 호출 (currentStep 감소)", async () => {
    const user = userEvent.setup();
    act(() => useSolutionWizardStore.getState().goToStep(3));
    renderLayout({ canProceed: true });

    await user.click(screen.getByRole("button", { name: PREV_BTN_LABEL }));

    expect(useSolutionWizardStore.getState().currentStep).toBe(2);
  });

  it("isSubmitting=true 시 이전 버튼 비활성화", () => {
    act(() => useSolutionWizardStore.getState().goToStep(2));
    renderLayout({ isSubmitting: true, canProceed: true });

    expect(screen.getByRole("button", { name: PREV_BTN_LABEL })).toBeDisabled();
  });

  it("마지막 스텝에서 다음 버튼 클릭 시 onSubmit 호출", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    act(() =>
      useSolutionWizardStore.getState().goToStep(SOLUTION_WIZARD_STEPS.length - 1)
    );
    renderLayout({ onSubmit, canProceed: true });

    await user.click(screen.getByRole("button", { name: SUBMIT_BTN_LABEL }));

    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it("현재 스텝 레이블이 heading으로 렌더링됨", () => {
    renderLayout();

    // h2 heading으로 현재 스텝 레이블 표시
    expect(
      screen.getByRole("heading", { name: SOLUTION_WIZARD_STEPS[0].label })
    ).toBeInTheDocument();
  });

  it("스텝 콘텐츠가 렌더링됨", () => {
    renderLayout();
    expect(screen.getByText("스텝 콘텐츠")).toBeInTheDocument();
  });

  it("nextLabel prop이 전달되면 다음 버튼 텍스트에 반영됨", async () => {
    // nextLabel은 aria-label이 아닌 버튼 텍스트에만 영향을 줌
    // aria-label은 isLast 여부에 따라 고정됨 — 텍스트 렌더링 확인
    const { container } = renderLayout({ canProceed: true, nextLabel: "이대로 진행" });

    // role="group" 내 두 번째 버튼 (next)의 텍스트 확인
    const navGroup = container.querySelector('[role="group"]');
    expect(navGroup?.textContent).toContain("이대로 진행");
  });
});
