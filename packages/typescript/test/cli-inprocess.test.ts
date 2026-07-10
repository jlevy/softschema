/**
 * In-process CLI tests. `standalone.test.ts` spawns the built `dist/cli.js` as a
 * subprocess (a real end-to-end check), but a subprocess is invisible to bun's V8 line
 * coverage, leaving `cli.ts` (the largest source file) uninstrumented. Driving the
 * exported `main(argv)` directly here exercises the same command paths in-process so the
 * coverage gate actually sees them. Stdout is captured into an array of chunks (not
 * printed) so tests can assert on CLI output; `captured()` returns the joined string.
 * The original write function is restored in afterEach.
 */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { main } from "../src/cli.js";

const REPO = resolve(import.meta.dir, "../../..");
const MOVIE_DOC = resolve(REPO, "examples/movie_page/spirited-away.md");
const MOVIE_SCHEMA = resolve(REPO, "examples/movie_page/movie-page.schema.yaml");
const MOVIE_README = resolve(REPO, "examples/movie_page/README.md");
const BAD_DOC = resolve(REPO, "tests/golden/fixtures/bad-error-norm.md");
const ERR_SCHEMA = resolve(REPO, "tests/golden/fixtures/error-norm.schema.yaml");
const PARITY_MODEL = resolve(REPO, "packages/typescript/test/fixtures/parity.ts");
const PARITY_SCHEMA = resolve(REPO, "examples/parity/parity.schema.yaml");

const argv = (...args: string[]) => ["node", "cli.js", ...args];

/* ---- stdout capture helper ---- */
let originalWrite: typeof process.stdout.write;
let chunks: string[] = [];

/** Return everything written to stdout since the last beforeEach reset. */
function captured(): string {
  return chunks.join("");
}

beforeEach(() => {
  originalWrite = process.stdout.write.bind(process.stdout);
  chunks = [];
  process.stdout.write = ((chunk: string | Uint8Array) => {
    chunks.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk));
    return true;
  }) as typeof process.stdout.write;
});
afterEach(() => {
  process.stdout.write = originalWrite;
});

describe("cli main() in-process", () => {
  test("doctor --json reports versioned capabilities", async () => {
    expect(await main(argv("doctor", "--json"))).toBe(0);
    const report = JSON.parse(captured());
    expect(report.protocol_version).toBe("1");
    expect(report.package.name).toBe("softschema");
    expect(report.runtime.name).toBe("bun");
    expect(report.capabilities.model_loaders).toEqual(["json-schema", "zod"]);
    expect(report.capabilities.operations).toContain("validate");
  });

  test("doctor text summarizes versioned capabilities", async () => {
    expect(await main(argv("doctor"))).toBe(0);
    expect(captured()).toContain("softschema discovery protocol: 1");
    expect(captured()).toContain("runtime: bun");
    expect(captured()).toContain("model loaders: json-schema, zod");
    expect(captured()).toContain("build: sha256:");
  });

  test("docs --list exits 0 and lists topics", async () => {
    expect(await main(argv("docs", "--list"))).toBe(0);
    expect(captured()).toContain("spec");
  });

  test("docs --list --json exits 0 and returns valid JSON", async () => {
    expect(await main(argv("docs", "--list", "--json"))).toBe(0);
    expect(() => JSON.parse(captured())).not.toThrow();
  });

  test("prime exits 0 with the skill rules and the docs index", async () => {
    expect(await main(argv("prime"))).toBe(0);
    const out = captured();
    expect(out).toContain("softschema");
    expect(out).toContain("Available softschema docs:");
  });

  test("docs <topic> prints a bundled doc (exit 0)", async () => {
    expect(await main(argv("docs", "spec"))).toBe(0);
    expect(captured().length).toBeGreaterThan(0);
  });

  test("docs example-pure-yaml prints the copyable artifact", async () => {
    expect(await main(argv("docs", "example-pure-yaml"))).toBe(0);
    expect(captured()).toContain('format: "1"');
    expect(captured()).toContain("contract: example.movies:MoviePage/v1");
    expect(captured()).not.toContain("---");
  });

  test("docs <unknown-topic> exits 2", async () => {
    expect(await main(argv("docs", "no-such-topic"))).toBe(2);
  });

  test("skill --brief exits 0 and prints skill text", async () => {
    expect(await main(argv("skill", "--brief"))).toBe(0);
    expect(captured()).toContain("softschema");
  });

  test("skill (rendered) exits 0 and prints skill text", async () => {
    expect(await main(argv("skill"))).toBe(0);
    expect(captured()).toContain("softschema");
  });

  test("inspect a compiled schema exits 0 and prints JSON", async () => {
    expect(await main(argv("inspect", MOVIE_SCHEMA))).toBe(0);
    expect(() => JSON.parse(captured())).not.toThrow();
    expect(JSON.parse(captured())).toHaveProperty("path");
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
    expect(captured()).toContain("structural");
  });

  test("validate with an undesignated multi-key envelope exits 2 (usage error)", async () => {
    const fixture = resolve(REPO, "tests/golden/fixtures/multi-key-no-envelope.md");
    expect(await main(argv("validate", fixture))).toBe(2);
  });

  test("validate a self-describing artifact with no flags exits 0", async () => {
    expect(await main(argv("validate", MOVIE_DOC))).toBe(0);
  });

  test("generate --check on the committed example exits 0 (no drift)", async () => {
    expect(await main(argv("generate", MOVIE_README, "--check"))).toBe(0);
  });

  test("compile --check matches the committed canonical schema (exit 0)", async () => {
    expect(
      await main(
        argv(
          "compile",
          `${PARITY_MODEL}:KitchenSink`,
          "--contract",
          "example.parity:KitchenSink/v1",
          "--out",
          PARITY_SCHEMA,
          "--check",
        ),
      ),
    ).toBe(0);
  });

  test("compile --check reports drift for a different contract id (exit 1)", async () => {
    expect(
      await main(
        argv("compile", `${PARITY_MODEL}:KitchenSink`, "--contract", "wrong:Sink/v1", "--out", PARITY_SCHEMA, "--check"),
      ),
    ).toBe(1);
    expect(captured()).toContain("drift");
  });

  test.each([
    ["--contract", "bad id"],
    ["--schema-id", "relative/schema"],
  ])("compile validates %s before importing a model", async (flag, value) => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-cli-identity-"));
    const marker = join(directory, "model-loaded");
    const model = join(directory, "model.mjs");
    const out = join(directory, "must-not-exist.yaml");
    writeFileSync(
      model,
      `import { writeFileSync } from "node:fs";\nwriteFileSync(${JSON.stringify(marker)}, "loaded");\nexport const Sample = {};\n`,
    );

    const args = ["compile", `${model}:Sample`, "--out", out, flag, value];
    if (flag === "--schema-id") args.push("--contract", "test:Sample/v1");
    expect(await main(argv(...args))).toBe(2);
    expect(existsSync(marker)).toBe(false);
    expect(existsSync(out)).toBe(false);
  });

  test("compile requires a contract before importing a model", async () => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-cli-identity-"));
    const marker = join(directory, "model-loaded");
    const model = join(directory, "model.mjs");
    const out = join(directory, "must-not-exist.yaml");
    writeFileSync(
      model,
      `import { writeFileSync } from "node:fs";\nwriteFileSync(${JSON.stringify(marker)}, "loaded");\nexport const Sample = {};\n`,
    );

    expect(await main(argv("compile", `${model}:Sample`, "--out", out))).toBe(2);
    expect(existsSync(marker)).toBe(false);
    expect(existsSync(out)).toBe(false);
  });

  test("validate checks an explicit contract before reading or importing", async () => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-cli-identity-"));
    const marker = join(directory, "model-loaded");
    const model = join(directory, "model.mjs");
    writeFileSync(
      model,
      `import { writeFileSync } from "node:fs";\nwriteFileSync(${JSON.stringify(marker)}, "loaded");\nexport const Sample = {};\n`,
    );

    expect(
      await main(
        argv(
          "validate",
          join(directory, "must-not-be-read.md"),
          "--contract",
          "bad id",
          "--model",
          `${model}:Sample`,
        ),
      ),
    ).toBe(2);
    expect(existsSync(marker)).toBe(false);
  });

  test("validate checks self-described metadata before importing a model", async () => {
    const directory = mkdtempSync(join(tmpdir(), "softschema-cli-identity-"));
    const marker = join(directory, "model-loaded");
    const model = join(directory, "model.mjs");
    const document = join(directory, "invalid.md");
    writeFileSync(
      model,
      `import { writeFileSync } from "node:fs";\nwriteFileSync(${JSON.stringify(marker)}, "loaded");\nexport const Sample = {};\n`,
    );
    writeFileSync(
      document,
      "---\nsoftschema:\n  contract: bad id\ndata: {}\n---\nbody\n",
    );

    expect(await main(argv("validate", document, "--model", `${model}:Sample`))).toBe(2);
    expect(existsSync(marker)).toBe(false);
  });

  test("--version prints 'softschema <version>' and exits 0", async () => {
    const code = await main(argv("--version"));
    expect(code).toBe(0);
    expect(captured()).toMatch(/^softschema \d+\.\d+\.\d+\n$/);
  });

  test("--help includes agent epilog text", async () => {
    const code = await main(argv("--help"));
    expect(code).toBe(0);
    expect(captured()).toContain("IMPORTANT for agents:");
    expect(captured()).toContain("softschema skill --brief");
    expect(captured()).toContain("uvx --from 'softschema==0.2.2' softschema");
    expect(captured()).toContain("npx --yes softschema@0.2.2");
  });

  test("validate --help documents the profile and default", async () => {
    const code = await main(argv("validate", "--help"));
    expect(code).toBe(0);
    expect(captured()).toContain("Artifact storage profile: frontmatter-md or pure-yaml");
    expect(captured()).toContain("default: frontmatter-md");
  });
});
