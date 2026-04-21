/**
 * StepCompanySolution — 폼 유효성 검증 테스트
 *
 * 검증 항목:
 * - 필수 필드 미입력 시 에러 메시지 표시 (필드 하이라이트)
 * - 솔루션 요구사항 50자 미만 시 에러 표시
 * - 유효한 입력 시 스토어 업데이트
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act } from "react";

import { StepCompanySolution } from "../step-company-solution";
import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

/* -- 모킹 -- */

// next-auth는 jsdom 환경에서 실행 불가 → mock
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
}));

/* -- 헬퍼 -- */

function renderStep() {
  return render(<StepCompanySolution />);
}

/* -- 테스트 -- */

describe("StepCompanySolution — 폼 유효성 검증", () => {
  beforeEach(() => {
    // 각 테스트 전 스토어 초기화
    act(() => useSolutionWizardStore.getState().reset());
  });

  it("초기 렌더링: 회사 이름, 솔루션 요구사항 입력 필드가 존재", () => {
    renderStep();

    expect(screen.getByLabelText(/회사 이름/i)).toBeInTheDocument();
    // 솔루션 요구사항 텍스트에리어
    expect(screen.getByLabelText(/필요한 솔루션 설명/i)).toBeInTheDocument();
  });

  it("솔루션 요구사항 50자 미만 입력 시 글자 수 부족 안내 표시", async () => {
    const user = userEvent.setup();
    renderStep();

    const textarea = screen.getByLabelText(/필요한 솔루션 설명/i);
    await user.type(textarea, "짧은 요청");

    // 최소 글자 수 미달 안내
    expect(screen.getByText(/최소.*자 더/)).toBeInTheDocument();
  });

  it("솔루션 요구사항 50자 이상 입력 시 부족 안내가 사라짐", async () => {
    const user = userEvent.setup();
    renderStep();

    const textarea = screen.getByLabelText(/필요한 솔루션 설명/i);
    const longText = "a".repeat(51);
    await user.type(textarea, longText);

    // 최소 50자 초과: 안내가 사라짐
    expect(screen.queryByText(/최소.*자 더/)).not.toBeInTheDocument();
  });

  it("회사 이름 입력 시 스토어의 companyName 업데이트", async () => {
    const user = userEvent.setup();
    renderStep();

    const input = screen.getByLabelText(/회사 이름/i);
    await user.type(input, "테스트 주식회사");

    await waitFor(() => {
      expect(
        useSolutionWizardStore.getState().data.company.companyName
      ).toBe("테스트 주식회사");
    });
  });

  it("주력 제품/서비스 입력 시 스토어의 mainProduct 업데이트", async () => {
    const user = userEvent.setup();
    renderStep();

    const input = screen.getByLabelText(/주력 제품\/서비스/i);
    await user.type(input, "B2B CRM 솔루션");

    await waitFor(() => {
      expect(
        useSolutionWizardStore.getState().data.company.mainProduct
      ).toBe("B2B CRM 솔루션");
    });
  });

  it("비즈니스 유형 B2B 버튼 클릭 시 스토어 업데이트", async () => {
    const user = userEvent.setup();
    renderStep();

    // accessible name: jsdom은 인접 span 사이 공백 없이 이어붙임
    // "B2B기업 대상" 형태 — B2B2C("B2B2C복합 모델")와 구분하기 위해 앵커 + 뒤 문자 확인
    const b2bButton = screen.getByRole("button", { name: /^B2B기업/i });
    await user.click(b2bButton);

    await waitFor(() => {
      expect(
        useSolutionWizardStore.getState().data.company.businessType
      ).toBe("b2b");
    });
  });

  it("글자 수 카운터: 초기값 0 / 2000 표시", () => {
    renderStep();

    expect(screen.getByText(/0 \/ 2000/)).toBeInTheDocument();
  });

  it("회사 규모 버튼이 5개 모두 렌더링됨", () => {
    renderStep();

    // accessible name: "스타트업 1–10명", "소기업 11–50명", etc.
    // 앵커 정규식으로 정확히 매칭 (중소기업 중복 방지)
    const sizes = [
      /^스타트업/i,
      /^소기업/i,
      /^중소기업/i,
      /^중견기업/i,
      /^대기업/i,
    ];
    sizes.forEach((regex) => {
      expect(
        screen.getByRole("button", { name: regex })
      ).toBeInTheDocument();
    });
  });

  it("업종 버튼 중 'IT/소프트웨어' 클릭 시 스토어 industry 업데이트", async () => {
    const user = userEvent.setup();
    renderStep();

    const itButton = screen.getByRole("button", { name: "IT/소프트웨어" });
    await user.click(itButton);

    await waitFor(() => {
      expect(
        useSolutionWizardStore.getState().data.company.industry
      ).toBe("it");
    });
  });
});
