import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { SeatObservabilityEntry } from "@/lib/api-client";

import { SeatRankingTable } from "@/components/dashboard/seat-widgets";

/** next-intl useTranslations 모킹 — 이 레포에 기존 render 테스트 선례가 없어 새로 정의.
 * key 를 그대로 반환하고 {value} 형태의 보간만 단순 치환한다. */
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

function seat(
  email: string,
  input: number,
  output: number,
  overrides: Partial<SeatObservabilityEntry> = {},
): SeatObservabilityEntry {
  return {
    account_email: email,
    seat_id: email,
    seat_status: "active",
    windows: [],
    usage_24h_input_tokens: input,
    usage_24h_output_tokens: output,
    ...overrides,
  };
}

describe("SeatRankingTable", () => {
  it("빈 items → 빈 상태 문구를 렌더한다", () => {
    render(<SeatRankingTable items={[]} />);
    expect(screen.getByText("seatRanking.empty")).toBeInTheDocument();
  });

  it("24h 사용량(input+output) 합산 내림차순으로 행을 렌더한다", () => {
    const items = [
      seat("low@example.com", 100, 100), // 200
      seat("high@example.com", 5000, 5000), // 10000
      seat("mid@example.com", 1000, 1000), // 2000
    ];

    render(<SeatRankingTable items={items} />);

    const rows = screen.getAllByRole("row");
    // rows[0] 은 헤더 행
    const bodyRows = rows.slice(1);
    expect(bodyRows).toHaveLength(3);

    const emails = bodyRows.map((row) => within(row).getAllByRole("cell")[1].textContent);
    expect(emails).toEqual([
      "high@example.com",
      "mid@example.com",
      "low@example.com",
    ]);
  });
});
