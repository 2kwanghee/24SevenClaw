import { afterEach, describe, expect, it, vi } from "vitest";

import { observability } from "../api-client";

function mockFetchOk(body: unknown) {
  return vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("observability.getSummary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("days 미지정 시 쿼리스트링 없이 요청", async () => {
    const fetchSpy = mockFetchOk({});
    await observability.getSummary("token");
    const url = fetchSpy.mock.calls[0][0] as string;
    expect(url).not.toContain("?");
  });

  it("days 지정 시 ?days=N 쿼리스트링으로 요청", async () => {
    const fetchSpy = mockFetchOk({});
    await observability.getSummary("token", { days: 14 });
    const url = fetchSpy.mock.calls[0][0] as string;
    expect(url).toContain("?days=14");
  });
});
