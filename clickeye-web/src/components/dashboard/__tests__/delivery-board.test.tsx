import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DeliveryBoardResponse } from "@/lib/api-client";

import { DeliveryBoard } from "../delivery-board";

/** next-intl useTranslations 모킹 — key 를 그대로 반환하고 {value} 보간만 단순 치환한다.
 * (기존 dashboard-seat-widgets.test.tsx 의 선례를 따름) */
vi.mock("next-intl", () => ({
  useTranslations: () => {
    const t = (key: string, values?: Record<string, string | number>) => {
      if (!values) return key;
      return Object.entries(values).reduce(
        (acc, [k, v]) => acc.replace(`{${k}}`, String(v)),
        key,
      );
    };
    t.has = () => true;
    return t;
  },
}));

const mockUseDeliveryBoard = vi.fn();
const mockUseAccessToken = vi.fn(() => "test-token");

vi.mock("@/hooks/use-observability", () => ({
  useDeliveryBoard: () => mockUseDeliveryBoard(),
}));

vi.mock("@/hooks/use-access-token", () => ({
  useAccessToken: () => mockUseAccessToken(),
}));

function mockBoard(response: DeliveryBoardResponse | undefined, extra: Record<string, unknown> = {}) {
  mockUseDeliveryBoard.mockReturnValue({
    data: response,
    isLoading: false,
    error: null,
    ...extra,
  });
}

describe("DeliveryBoard", () => {
  beforeEach(() => {
    mockUseDeliveryBoard.mockReset();
    // matchMedia 모킹 — 기본은 reduced-motion 아님(애니메이션 활성 경로 커버)
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });
  });

  it("목데이터로 8단계 컬럼 헤더를 렌더한다", () => {
    mockBoard({
      projects: [
        {
          project_id: "p1",
          name: "Project One",
          intake_status: "accepted",
          stages: { received_at: "2026-01-01T00:00:00Z" },
          tickets: [],
        },
      ],
    });

    render(<DeliveryBoard />);

    for (const col of [
      "columns.received",
      "columns.refined",
      "columns.accepted",
      "columns.issued",
      "columns.implementing",
      "columns.qa",
      "columns.gate",
      "columns.done",
    ]) {
      expect(screen.getByText(col)).toBeInTheDocument();
    }
  });

  it("티켓이 매핑된 컬럼(카드)에 나타난다", () => {
    mockBoard({
      projects: [
        {
          project_id: "p1",
          name: "Project One",
          intake_status: "accepted",
          tickets: [
            {
              key: "CE-100",
              title: "구현 중인 티켓",
              stage: "implementing",
              stage_history: [
                { stage: "issued", at: "2026-01-01T00:00:00Z" },
                { stage: "implementing", at: "2026-01-02T00:00:00Z" },
              ],
              active: true,
            },
          ],
        },
      ],
    });

    render(<DeliveryBoard />);

    // 데스크톱(그리드)·모바일(스택) 두 레이아웃이 동시에 DOM 에 존재(hidden 클래스는 jsdom 에서
    // 레이아웃을 감추지 않음) — 최소 1곳 이상에 렌더되는지로 검증한다.
    expect(screen.getAllByText("CE-100").length).toBeGreaterThan(0);
    expect(screen.getAllByText("구현 중인 티켓").length).toBeGreaterThan(0);
  });

  it("outcome=failed 티켓은 danger 카드로 렌더한다", () => {
    mockBoard({
      projects: [
        {
          project_id: "p1",
          name: "Project One",
          intake_status: "accepted",
          tickets: [
            {
              key: "CE-200",
              title: "실패한 티켓",
              stage: "failed",
              outcome: "failed",
              stage_history: [{ stage: "gate", at: "2026-01-01T00:00:00Z" }],
            },
          ],
        },
      ],
    });

    render(<DeliveryBoard />);

    const cards = screen.getAllByTestId("delivery-board-ticket-card");
    expect(cards.length).toBeGreaterThan(0);
    expect(cards.every((card) => card.getAttribute("data-danger") === "true")).toBe(true);
    expect(screen.getAllByText("failedBadge").length).toBeGreaterThan(0);
  });

  it("outcome=unknown/demoted 라도 stage=failed 면 danger 카드로 렌더한다", () => {
    // 백엔드(observability_service.py `_derive_ticket_progress`)는 성공 도메인 밖 outcome
    // 전체(unknown/demoted/None 포함)를 stage=failed 로 묶는다 — outcome 리터럴이 아니라
    // stage 를 봐야 한다(회귀: outcome 만 보면 이 케이스를 놓친다).
    mockBoard({
      projects: [
        {
          project_id: "p1",
          name: "Project One",
          intake_status: "accepted",
          tickets: [
            {
              key: "CE-201",
              title: "판정 보류로 실패 처리된 티켓",
              stage: "failed",
              outcome: "demoted",
              stage_history: [{ stage: "gate", at: "2026-01-01T00:00:00Z" }],
            },
          ],
        },
      ],
    });

    render(<DeliveryBoard />);

    const cards = screen.getAllByTestId("delivery-board-ticket-card");
    expect(cards.length).toBeGreaterThan(0);
    expect(cards.every((card) => card.getAttribute("data-danger") === "true")).toBe(true);
  });

  it("프로젝트가 0건이면 empty 문구를 렌더한다", () => {
    mockBoard({ projects: [] });

    render(<DeliveryBoard />);

    expect(screen.getByText("empty")).toBeInTheDocument();
  });

  it("reduced-motion 이면 애니메이션 엘리먼트를 렌더하지 않는다", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    mockBoard({
      projects: [
        {
          project_id: "p1",
          name: "Project One",
          intake_status: "accepted",
          tickets: [
            {
              key: "CE-300",
              title: "활성 티켓",
              stage: "qa",
              stage_history: [
                { stage: "implementing", at: "2026-01-01T00:00:00Z" },
                { stage: "qa", at: "2026-01-02T00:00:00Z" },
              ],
              active: true,
            },
          ],
        },
      ],
    });

    render(<DeliveryBoard />);

    expect(screen.queryAllByTestId("delivery-board-flow-animated")).toHaveLength(0);
    expect(screen.getAllByTestId("delivery-board-flow-static").length).toBeGreaterThan(0);
  });
});
