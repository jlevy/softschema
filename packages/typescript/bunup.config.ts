import { defineConfig } from "bunup";

export default defineConfig({
  entry: ["src/index.ts", "src/node.ts", "src/core/index.ts", "src/cli.ts"],
  format: ["esm"],
  target: "node",
  dts: true,
  clean: true,
});
