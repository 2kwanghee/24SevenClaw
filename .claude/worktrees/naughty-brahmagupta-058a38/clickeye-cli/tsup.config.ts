import { defineConfig } from "tsup";
import { cp } from "node:fs/promises";

export default defineConfig({
  entry: ["src/cli.ts"],
  format: ["esm"],
  target: "node18",
  outDir: "dist",
  clean: true,
  splitting: false,
  sourcemap: true,
  dts: true,
  shims: true,
  async onSuccess() {
    await cp("src/templates", "dist/templates", { recursive: true });
    await cp("src/catalog", "dist/catalog", { recursive: true });
  },
});
