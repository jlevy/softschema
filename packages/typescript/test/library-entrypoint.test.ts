/**
 * Regression tests for the library entrypoint (issue #16).
 *
 * Two packaging bugs are guarded here:
 *  1. The built `index.js` once listed re-exports that the bundler had tree-shaken
 *     away (a side effect of `"sideEffects": false` on a pure re-export barrel), so
 *     `import { validateArtifact } from "softschema"` threw `SyntaxError: Export 'X'
 *     is not defined` at load time.
 *  2. The CLI's `isMain` guard lowered to an always-true CommonJS check, so importing
 *     the module (e.g. via the `./cli` subpath) executed the CLI instead of just
 *     exposing its API.
 *
 * Every check runs the built output in a fresh Node process (not Bun), matching how a
 * published consumer loads the package. The build runs in `beforeAll` so the test is
 * self-contained regardless of run order.
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { beforeAll, describe, expect, test } from "bun:test";

const PACKAGE_ROOT = resolve(import.meta.dir, "..");
const INDEX = join(PACKAGE_ROOT, "dist", "index.js");
const CLI = join(PACKAGE_ROOT, "dist", "cli.js");

beforeAll(() => {
  const build = spawnSync("bun", ["run", "build"], { cwd: PACKAGE_ROOT, encoding: "utf8" });
  if (build.status !== 0) throw new Error(`build failed: ${build.stderr}`);
}, 120_000);

interface RunResult {
  status: number | null;
  stdout: string;
  stderr: string;
}

// Run `body` (an ESM snippet) from a real script file under Node, with CLI-style argv.
// Using a real file (not `node -e`) means argv[1] is a genuine path, mirroring how a
// consumer app loads the package.
function runConsumer(body: string): RunResult {
  const dir = mkdtempSync(join(tmpdir(), "softschema-entry-"));
  const script = join(dir, "consumer.mjs");
  writeFileSync(script, body);
  const r = spawnSync("node", [script, "validate", "bogus.md"], { encoding: "utf8" });
  return { status: r.status, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

const indexUrl = () => pathToFileURL(INDEX).href;
const cliUrl = () => pathToFileURL(CLI).href;

describe("library entrypoint (issue #16)", () => {
  test("named import of validateArtifact and parseSchemaMetadata resolves to callables", () => {
    const r = runConsumer(
      `import { validateArtifact, parseSchemaMetadata } from ${JSON.stringify(indexUrl())};\n` +
        `process.stdout.write(typeof validateArtifact + " " + typeof parseSchemaMetadata);\n`,
    );
    expect(r.stderr).toBe("");
    expect(r.stdout).toBe("function function");
    expect(r.status).toBe(0);
  });

  test("importing the entrypoint runs no CLI behavior", () => {
    const r = runConsumer(`await import(${JSON.stringify(indexUrl())});\nprocess.stdout.write("index-ok");\n`);
    expect(r.stderr).toBe("");
    expect(r.stdout).toBe("index-ok");
    expect(r.status).toBe(0);
  });

  test("runtime exports are exactly the supported value surface", () => {
    const r = runConsumer(
      `const api = await import(${JSON.stringify(indexUrl())});\n` +
        `process.stdout.write(JSON.stringify(Object.keys(api).sort()));\n`,
    );
    expect(JSON.parse(r.stdout)).toEqual([
      "Contracts",
      "EnvelopeAmbiguityError",
      "SchemaView",
      "compileSchema",
      "inferEnvelopeKey",
      "parseSchemaMetadata",
      "regenerate",
      "softField",
      "validateArtifact",
      "validateSemantic",
      "validateStructural",
      "validateValues",
    ]);
  });

  test("importing the ./cli module runs no CLI behavior", () => {
    const r = runConsumer(`await import(${JSON.stringify(cliUrl())});\nprocess.stdout.write("cli-ok");\n`);
    expect(r.stderr).toBe("");
    expect(r.stdout).toBe("cli-ok");
    expect(r.status).toBe(0);
  });

  test("type declarations expose the public ESM consumer surface", () => {
    const dts = readFileSync(join(PACKAGE_ROOT, "dist", "index.d.ts"), "utf8");
    for (const sym of [
      "validateArtifact",
      "parseSchemaMetadata",
      "SchemaMetadata",
      "Contract",
      "ArtifactValidationResult",
    ]) {
      expect(dts).toContain(sym);
    }
  });
});
