import { afterEach, describe, expect, it } from "vitest";

import { isModernizeEnabled } from "../feature-flags";

const ENV_KEY = "NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED";
const ORIGINAL = process.env[ENV_KEY];

afterEach(() => {
  if (ORIGINAL === undefined) {
    delete process.env[ENV_KEY];
  } else {
    process.env[ENV_KEY] = ORIGINAL;
  }
});

describe("isModernizeEnabled", () => {
  it("env 가 'true' 일 때 true", () => {
    process.env[ENV_KEY] = "true";
    expect(isModernizeEnabled()).toBe(true);
  });

  it("env 가 'false' 일 때 false", () => {
    process.env[ENV_KEY] = "false";
    expect(isModernizeEnabled()).toBe(false);
  });

  it("env 미설정 시 default false (안전한 OFF)", () => {
    delete process.env[ENV_KEY];
    expect(isModernizeEnabled()).toBe(false);
  });

  it("env 가 'TRUE' 등 다른 값일 때 false (strict 비교)", () => {
    process.env[ENV_KEY] = "TRUE";
    expect(isModernizeEnabled()).toBe(false);
    process.env[ENV_KEY] = "1";
    expect(isModernizeEnabled()).toBe(false);
    process.env[ENV_KEY] = "";
    expect(isModernizeEnabled()).toBe(false);
  });
});
