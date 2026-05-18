import { describe, expect, it } from "vitest";

import {
  checkIntegrationInput,
  checkLinearInputs,
  checkNotionInputs,
  describeIntegrationError,
  sanitizeIntegrationInput,
} from "../integration-validators";

describe("sanitizeIntegrationInput", () => {
  it("printable ASCII 는 그대로 통과", () => {
    expect(sanitizeIntegrationInput("lin_api_abc123-XYZ_!.")).toBe(
      "lin_api_abc123-XYZ_!.",
    );
  });

  it("한글이 섞이면 한글만 제거", () => {
    expect(sanitizeIntegrationInput("lin한_api_abc글123")).toBe("lin_api_abc123");
  });

  it("순수 한글 입력은 빈 문자열", () => {
    expect(sanitizeIntegrationInput("한글입력")).toBe("");
  });

  it("이모지/제어문자도 제거", () => {
    expect(sanitizeIntegrationInput("linkey🎉end")).toBe("linkeyend");
  });

  it("빈 문자열은 빈 문자열", () => {
    expect(sanitizeIntegrationInput("")).toBe("");
  });
});

describe("checkIntegrationInput / checkLinearInputs / checkNotionInputs", () => {
  it("ASCII 만 있으면 ok", () => {
    expect(checkIntegrationInput("lin_api_abc", "Linear API Key").ok).toBe(true);
  });

  it("한글이 포함되면 ok=false + 안내 메시지", () => {
    const r = checkIntegrationInput("한글키", "Linear API Key");
    expect(r.ok).toBe(false);
    expect(r.message).toContain("Linear API Key");
    expect(r.message).toContain("비-ASCII");
  });

  it("Linear: api key 또는 team id 중 하나만 한글이어도 invalid", () => {
    expect(checkLinearInputs("lin_api_abc", "팀ID").ok).toBe(false);
    expect(checkLinearInputs("한글", "team-uuid").ok).toBe(false);
    expect(checkLinearInputs("lin_api_abc", "team-uuid").ok).toBe(true);
  });

  it("Notion: 동일 로직", () => {
    expect(checkNotionInputs("secret_abc", "db-uuid").ok).toBe(true);
    expect(checkNotionInputs("한글", "db-uuid").ok).toBe(false);
  });
});

describe("describeIntegrationError", () => {
  it("'Failed to fetch' TypeError 는 연결 안내 메시지", () => {
    const err = new TypeError("Failed to fetch");
    expect(describeIntegrationError(err)).toContain("연결할 수 없습니다");
  });

  it("일반 Error 는 message 포함", () => {
    expect(describeIntegrationError(new Error("400 Bad Request"))).toContain(
      "400 Bad Request",
    );
  });

  it("Error 가 아닌 throw 는 기본 메시지", () => {
    expect(describeIntegrationError("string error")).toBe(
      "검증 요청 실패. 네트워크를 확인하세요.",
    );
  });
});
