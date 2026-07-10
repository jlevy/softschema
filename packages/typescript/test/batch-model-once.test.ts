import { expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

test("batch validation loads one semantic model for every prepared artifact", () => {
  const directory = mkdtempSync(join(tmpdir(), "softschema-model-once-"));
  const first = join(directory, "first.yaml");
  const second = join(directory, "second.yaml");
  const marker = join(directory, "loads.txt");
  const preload = join(directory, "preload.ts");
  const runner = join(directory, "runner.ts");
  const sourceRoot = resolve(import.meta.dir, "../src");
  const loaderUrl = pathToFileURL(join(sourceRoot, "model-loader.js")).href;
  const cliUrl = pathToFileURL(join(sourceRoot, "cli.ts")).href;
  const zodUrl = import.meta.resolve("zod");
  writeFileSync(first, "name: A\ncount: 1\n");
  writeFileSync(second, "name: B\ncount: 2\n");
  writeFileSync(
    preload,
    `import { mock } from "bun:test";
import { appendFileSync } from "node:fs";
import { z } from ${JSON.stringify(zodUrl)};
mock.module(${JSON.stringify(loaderUrl)}, () => ({
  loadZodModel: async () => {
    appendFileSync(${JSON.stringify(marker)}, "load\\n");
    return z.object({ name: z.string(), count: z.number() });
  },
}));
`,
  );
  writeFileSync(
    runner,
    `const { main } = await import(${JSON.stringify(`${cliUrl}?model-once`)});
const code = await main([
  "node", "cli.js", "validate",
  ${JSON.stringify(first)}, ${JSON.stringify(second)},
  "--profile", "pure-yaml",
  "--contract", "test.batch:Record/v1",
  "--model", "trusted.mjs:Record",
]);
process.exitCode = code;
`,
  );

  const child = Bun.spawnSync({
    cmd: [process.execPath, "--preload", preload, runner],
    stdout: "pipe",
    stderr: "pipe",
  });

  expect({ exitCode: child.exitCode, stderr: child.stderr.toString() }).toEqual({
    exitCode: 0,
    stderr: "",
  });
  expect(JSON.parse(child.stdout.toString()).summary.passed).toBe(2);
  expect(readFileSync(marker, "utf8").trimEnd().split("\n")).toEqual(["load"]);
});
