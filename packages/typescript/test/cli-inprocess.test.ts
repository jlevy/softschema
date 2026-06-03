/**
 * In-process CLI coverage. `standalone.test.ts` spawns the built `dist/cli.js` as a
 * subprocess (a real end-to-end check), but a subprocess is invisible to bun's V8 line
 * coverage, leaving `cli.ts` (the largest source file) uninstrumented. Driving the
 * exported `main(argv)` directly here exercises the same command paths in-process so the
 * coverage gate actually sees them. Output is suppressed to keep the test log clean.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { resolve } from "node:path";
import { main } from "../src/cli.ts";

const REPO = resolve(import.meta.dir, "../../..");
const MOVIE_DOC = resolve(REPO, "examples/movie_page/spirited-away.md");
const MOVIE_SCHEMA = resolve(REPO, "examples/movie_page/movie-page.schema.yaml");
const MOVIE_README = resolve(REPO, "examples/movie_page/README.md");
const BAD_DOC = resolve(REPO, "tests/golden/fixtures/bad-error-norm.md");
const ERR_SCHEMA = resolve(REPO, "tests/golden/fixtures/error-norm.schema.yaml");
const PARITY_MODEL = resolve(REPO, "packages/typescript/test/fixtures/parity.ts");
const PARITY_SIDECAR = resolve(REPO, "examples/parity/parity.schema.yaml");

const argv = (...args: string[]) => ["node", "cli.js", ...args];

let originalWrite: typeof process.stdout.write;
beforeEach(() => {
  originalWrite = process.stdout.write.bind(process.stdout);
  process.stdout.write = (() => true) as typeof process.stdout.write;
});
afterEach(() => {
  process.stdout.write = originalWrite;
});

describe("cli main() in-process", () => {
  test("docs --list exits 0", async () => {
    expect(await main(argv("docs", "--list"))).toBe(0);
  });

  test("docs --list --json exits 0", async () => {
    expect(await main(argv("docs", "--list", "--json"))).toBe(0);
  });

  test("docs <topic> prints a bundled doc (exit 0)", async () => {
    expect(await main(argv("docs", "spec"))).toBe(0);
  });

  test("docs <unknown-topic> exits 2", async () => {
    expect(await main(argv("docs", "no-such-topic"))).toBe(2);
  });

  test("skill --brief exits 0", async () => {
    expect(await main(argv("skill", "--brief"))).toBe(0);
  });

  test("skill (rendered) exits 0", async () => {
    expect(await main(argv("skill"))).toBe(0);
  });

  test("inspect a schema sidecar exits 0", async () => {
    expect(await main(argv("inspect", MOVIE_SCHEMA))).toBe(0);
  });

  test("validate (structural ok) exits 0", async () => {
    expect(await main(argv("validate", MOVIE_DOC, "--schema", MOVIE_SCHEMA, "--envelope", "movie"))).toBe(0);
  });

  test("validate (structural failure) exits 1", async () => {
    expect(
      await main(
        argv("validate", BAD_DOC, "--schema", ERR_SCHEMA, "--contract", "test.errors:Sample/v1", "--envelope", "data"),
      ),
    ).toBe(1);
  });

  test("validate with no implementation exits 2 (usage error)", async () => {
    expect(await main(argv("validate", MOVIE_DOC, "--contract", "x:Y/v1"))).toBe(2);
  });

  test("generate --check on the committed example exits 0 (no drift)", async () => {
    expect(await main(argv("generate", MOVIE_README, "--check"))).toBe(0);
  });

  test("compile --check matches the committed canonical sidecar (exit 0)", async () => {
    expect(
      await main(
        argv(
          "compile",
          `${PARITY_MODEL}:KitchenSink`,
          "--contract",
          "example.parity:KitchenSink/v1",
          "--out",
          PARITY_SIDECAR,
          "--check",
        ),
      ),
    ).toBe(0);
  });

  test("compile --check reports drift for a different contract id (exit 1)", async () => {
    expect(
      await main(
        argv("compile", `${PARITY_MODEL}:KitchenSink`, "--contract", "wrong:Sink/v1", "--out", PARITY_SIDECAR, "--check"),
      ),
    ).toBe(1);
  });
});
