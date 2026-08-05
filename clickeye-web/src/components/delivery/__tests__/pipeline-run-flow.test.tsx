import { describe, expect, it } from "vitest";

import type { PipelineRun, PipelineRunEvent } from "@/lib/api-client";
import {
  aggregatePipelineUsage,
  computePipelineStages,
  hasModelMismatch,
  STAGE_KEYS,
  type StageStatus,
} from "../pipeline-run-flow";

/** occurred_at 을 순차 부여하는 이벤트 빌더(연속 차이로 유도되는 소요시간 검증용). */
function ev(
  event: string,
  data: Record<string, unknown> = {},
  occurred_at: string | null = null,
): PipelineRunEvent {
  return {
    event,
    data,
    occurred_at,
    created_at: occurred_at ?? "2026-08-04T00:00:00Z",
  };
}

/** 단계 키 → 상태 로 뽑아 비교하기 쉽게 만든다. */
function statusMap(events: PipelineRunEvent[]): Record<string, StageStatus> {
  const out: Record<string, StageStatus> = {};
  for (const s of computePipelineStages(events)) out[s.key] = s.status;
  return out;
}

describe("computePipelineStages", () => {
  it("5 이벤트 전부 있는 성공 런 → 모든 단계 done", () => {
    const events = [
      ev("refine_done", { refined: true }),
      ev("impl_done", { duration_s: 25 }),
      ev("qa_done", { ran: true, exit: 0 }),
      ev("gate_done", { verdict: "direct" }),
      ev("run_done", { outcome: "pushed" }),
    ];
    expect(statusMap(events)).toEqual({
      refine: "done",
      impl: "done",
      qa: "done",
      gate: "done",
      done: "done",
    });
  });

  it("qa_done.exit=1 → qa 는 failed, 이후 단계는 pending", () => {
    const events = [
      ev("refine_done"),
      ev("impl_done", { duration_s: 30 }),
      ev("qa_done", { ran: true, exit: 1 }),
    ];
    const m = statusMap(events);
    expect(m.qa).toBe("failed");
    expect(m.gate).toBe("pending");
    expect(m.done).toBe("pending");
  });

  it("run_done.outcome=failed → done 노드는 failed", () => {
    const events = [
      ev("refine_done"),
      ev("impl_done", { duration_s: 10 }),
      ev("qa_done", { ran: true, exit: 0 }),
      ev("gate_done", { verdict: "direct" }),
      ev("run_done", { outcome: "failed" }),
    ];
    expect(statusMap(events).done).toBe("failed");
  });

  it("run_done 없음 → 다음 단계는 진행 추정(inferred), 그 뒤는 pending", () => {
    const events = [ev("refine_done"), ev("impl_done", { duration_s: 25 })];
    const m = statusMap(events);
    expect(m.refine).toBe("done");
    expect(m.impl).toBe("done");
    expect(m.qa).toBe("inferred");
    expect(m.gate).toBe("pending");
    expect(m.done).toBe("pending");
  });

  it("추정 진행은 정확히 한 노드에만 부여된다", () => {
    const events = [ev("refine_done")];
    const stages = computePipelineStages(events);
    const inferred = stages.filter((s) => s.status === "inferred");
    expect(inferred).toHaveLength(1);
    expect(inferred[0].key).toBe("impl");
  });

  it("이벤트 0건 → 모든 단계 pending (추정 없음)", () => {
    const stages = computePipelineStages([]);
    expect(stages).toHaveLength(STAGE_KEYS.length);
    expect(stages.every((s) => s.status === "pending")).toBe(true);
  });

  it("gate_done 없이 run_done 이 있는 완료 런 → gate 는 skipped, done 은 done", () => {
    // 거버넌스 비활성 경로: gate_done 이 기록되지 않는다. "대기"가 아니라 "기록 없음".
    const events = [
      ev("refine_done"),
      ev("impl_done", { duration_s: 25 }),
      ev("qa_done", { ran: true, exit: 0 }),
      ev("run_done", { outcome: "pushed" }),
    ];
    const m = statusMap(events);
    expect(m.gate).toBe("skipped");
    expect(m.done).toBe("done");
    // run_done 이 있으므로 어떤 단계도 pending/inferred 가 아니다.
    const stages = computePipelineStages(events);
    expect(stages.some((s) => s.status === "pending")).toBe(false);
    expect(stages.some((s) => s.status === "inferred")).toBe(false);
  });

  it("run_done 이 없으면 기록 없는 단계는 skipped 가 아니라 pending/inferred 로 남는다", () => {
    const events = [ev("refine_done"), ev("impl_done", { duration_s: 25 })];
    const stages = computePipelineStages(events);
    expect(stages.some((s) => s.status === "skipped")).toBe(false);
    expect(statusMap(events).qa).toBe("inferred");
  });

  it("model_mismatch 만 추가돼도 단계 판정은 불변이고 경고만 감지된다", () => {
    const base = [
      ev("refine_done"),
      ev("impl_done", { duration_s: 25 }),
      ev("qa_done", { ran: true, exit: 0 }),
      ev("gate_done", { verdict: "direct" }),
      ev("run_done", { outcome: "pushed" }),
    ];
    const withMismatch = [...base, ev("model_mismatch", { expected: "sonnet" })];
    expect(statusMap(withMismatch)).toEqual(statusMap(base));
    expect(hasModelMismatch(withMismatch)).toBe(true);
    expect(hasModelMismatch(base)).toBe(false);
  });

  it("impl 소요시간은 duration_s 실측(유도 아님), 나머지는 occurred_at 차이로 유도", () => {
    const events = [
      ev("refine_done", {}, "2026-08-04T10:00:00Z"),
      ev("impl_done", { duration_s: 42 }, "2026-08-04T10:00:45Z"),
      ev("qa_done", { ran: true, exit: 0 }, "2026-08-04T10:01:05Z"),
    ];
    const stages = computePipelineStages(events);
    const impl = stages.find((s) => s.key === "impl")!;
    const qa = stages.find((s) => s.key === "qa")!;
    expect(impl.durationS).toBe(42);
    expect(impl.durationDerived).toBe(false);
    // qa: impl(10:00:45) → qa(10:01:05) = 20초, 유도값
    expect(qa.durationS).toBe(20);
    expect(qa.durationDerived).toBe(true);
  });
});

/** issue_key 별 usage 를 가진 최소 런 객체 빌더. */
function run(
  issueKey: string,
  usage: { input: number; output: number; cache: number; models?: string[] },
): PipelineRun {
  return {
    run_id: `${issueKey}-${Math.random()}`,
    issue_key: issueKey,
    project_id: "p1",
    workspace_key: "workspace",
    started_at: null,
    ended_at: null,
    duration_s: null,
    outcome: null,
    events: [],
    usage: {
      models: usage.models ?? [],
      input_tokens: usage.input,
      output_tokens: usage.output,
      cache_read_tokens: usage.cache,
      ref_cost_usd: null,
    },
  };
}

describe("aggregatePipelineUsage", () => {
  it("서로 다른 티켓은 그대로 합산된다", () => {
    const runs = [
      run("CE-1", { input: 100, output: 10, cache: 1000 }),
      run("CE-2", { input: 200, output: 20, cache: 2000 }),
    ];
    const u = aggregatePipelineUsage(runs);
    expect(u.input_tokens).toBe(300);
    expect(u.output_tokens).toBe(30);
    expect(u.cache_read_tokens).toBe(3000);
    expect(u.ticketCount).toBe(2);
    expect(u.runCount).toBe(2);
  });

  it("같은 티켓의 런 2건은 1회만 합산된다(이중계상 방지)", () => {
    // usage 는 티켓 단위 집계라 같은 issue_key 의 두 런에 동일 값이 실린다.
    const runs = [
      run("CE-9", { input: 500, output: 50, cache: 9000 }),
      run("CE-9", { input: 500, output: 50, cache: 9000 }),
    ];
    const u = aggregatePipelineUsage(runs);
    expect(u.input_tokens).toBe(500);
    expect(u.output_tokens).toBe(50);
    expect(u.cache_read_tokens).toBe(9000);
    expect(u.ticketCount).toBe(1);
    expect(u.runCount).toBe(2);
  });

  it("같은 티켓 2런 + 다른 티켓 1런 → 2티켓분만 합산(런 3건)", () => {
    const runs = [
      run("CE-9", { input: 500, output: 50, cache: 9000 }),
      run("CE-9", { input: 500, output: 50, cache: 9000 }),
      run("CE-3", { input: 100, output: 10, cache: 1000 }),
    ];
    const u = aggregatePipelineUsage(runs);
    // CE-9 은 1회만, CE-3 1회 → 600 / 60 / 10000
    expect(u.input_tokens).toBe(600);
    expect(u.output_tokens).toBe(60);
    expect(u.cache_read_tokens).toBe(10000);
    expect(u.ticketCount).toBe(2);
    expect(u.runCount).toBe(3);
  });

  it("models 는 티켓 간 합집합으로 중복 제거된다", () => {
    const runs = [
      run("CE-1", { input: 1, output: 1, cache: 1, models: ["sonnet", "haiku"] }),
      run("CE-1", { input: 1, output: 1, cache: 1, models: ["sonnet", "haiku"] }),
      run("CE-2", { input: 1, output: 1, cache: 1, models: ["opus", "sonnet"] }),
    ];
    expect(aggregatePipelineUsage(runs).models).toEqual([
      "sonnet",
      "haiku",
      "opus",
    ]);
  });

  it("빈 배열 → 0 합산", () => {
    const u = aggregatePipelineUsage([]);
    expect(u).toEqual({
      input_tokens: 0,
      output_tokens: 0,
      cache_read_tokens: 0,
      models: [],
      ticketCount: 0,
      runCount: 0,
    });
  });
});
