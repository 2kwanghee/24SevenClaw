import nextConfig from "eslint-config-next";

/** @type {import("eslint").Linter.Config[]} */
const config = [
  ...nextConfig,
  {
    rules: {
      // 사용하지 않는 변수 경고
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  {
    ignores: [".next/", "node_modules/"],
  },
];

export default config;
