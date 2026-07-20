import nextConfig from "eslint-config-next";
import tseslint from "typescript-eslint";

/** @type {import("eslint").Linter.Config[]} */
const config = [
  ...nextConfig,
  {
    // @typescript-eslint 플러그인은 룰을 적용하는 config object에 함께 등록해야 한다 (flat config 규칙)
    plugins: {
      "@typescript-eslint": tseslint.plugin,
    },
    rules: {
      // 사용하지 않는 변수 경고
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // React Compiler 순수성 규칙: 기존 코드 패턴을 막지 않도록 경고로 유지 (CI 차단 방지)
      "react-hooks/purity": "warn",
    },
  },
  {
    ignores: [".next/", "node_modules/"],
  },
];

export default config;
