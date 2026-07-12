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
import { chmodSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { resolve } from "node:path";
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
let originalErrorWrite: typeof process.stderr.write;
let originalPath: string | undefined;
let chunks: string[] = [];
let errorChunks: string[] = [];

/** Return everything written to stdout since the last beforeEach reset. */
function captured(): string {
  return chunks.join("");
}

beforeEach(() => {
  originalWrite = process.stdout.write.bind(process.stdout);
  originalErrorWrite = process.stderr.write.bind(process.stderr);
  originalPath = process.env.PATH;
  chunks = [];
  errorChunks = [];
  process.stdout.write = ((chunk: string | Uint8Array) => {
    chunks.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk));
    return true;
  }) as typeof process.stdout.write;
  process.stderr.write = ((chunk: string | Uint8Array) => {
    errorChunks.push(typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk));
    return true;
  }) as typeof process.stderr.write;
});
afterEach(() => {
  process.stdout.write = originalWrite;
  process.stderr.write = originalErrorWrite;
  process.env.PATH = originalPath;
});

describe("cli main() in-process", () => {
  test("doctor --json reports available runners", async () => {
    const bin = mkdtempSync(join(tmpdir(), "softschema-doctor-"));
    for (const name of ["softschema", "uvx"]) {
      const path = join(bin, name);
      writeFileSync(path, "#!/bin/sh\nexit 0\n");
      chmodSync(path, 0o755);
    }
    process.env.PATH = bin;

    expect(await main(argv("doctor", "--json"))).toBe(0);
    const report = JSON.parse(captured());
    expect(report.recommended_invocation).toBe("softschema");
    expect(report.runners).toEqual([
      { name: "softschema", available: true, path: join(bin, "softschema") },
      { name: "uvx", available: true, path: join(bin, "uvx") },
      { name: "npx", available: false, path: null },
    ]);
    // Version is read from package.json; assert shape, not a pinned literal.
    expect(report.version).toMatch(/^\d+\.\d+\.\d+/);
  });

  test("doctor text tells users how to recover when no runner exists", async () => {
    process.env.PATH = mkdtempSync(join(tmpdir(), "softschema-doctor-empty-"));

    expect(await main(argv("doctor"))).toBe(0);
    expect(captured()).toContain("softschema version:");
    expect(captured()).toContain("recommended invocation: unavailable");
    expect(captured()).toContain("Install uv or Node");
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

  test("loads a model whose filesystem path needs URL escaping", async () => {
    const dir = mkdtempSync(join(tmpdir(), "softschema model #"));
    const modulePath = join(dir, "movie model #%.mjs");
    const fixtureUrl = new URL("./fixtures/movie-model.mjs", import.meta.url).href;
    writeFileSync(modulePath, `export { MoviePage } from ${JSON.stringify(fixtureUrl)};\n`);
    try {
      expect(await main(argv("validate", MOVIE_DOC, "--model", `${modulePath}:MoviePage`))).toBe(0);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("explains model file support when an import fails", async () => {
    const missing = join(tmpdir(), "missing model.ts");
    expect(await main(argv("validate", MOVIE_DOC, "--model", `${missing}:MoviePage`))).toBe(2);
    expect(errorChunks.join("")).toContain(
      "Node model paths must name built JavaScript (.js or .mjs); Bun may load TypeScript directly.",
    );
  });

  test("rejects a document schema symlink that escapes its directory", async () => {
    const root = mkdtempSync(join(tmpdir(), "softschema-schema-link-"));
    const docs = join(root, "docs");
    const outside = join(root, "outside.schema.yaml");
    const doc = join(docs, "artifact.md");
    const linked = join(docs, "linked.schema.yaml");
    mkdirSync(docs);
    writeFileSync(outside, "type: object\n");
    writeFileSync(
      doc,
      "---\nsoftschema:\n  contract: example:Linked/v1\n  schema: linked.schema.yaml\nvalue: {}\n---\n",
    );
    symlinkSync(outside, linked);
    try {
      expect(await main(argv("validate", doc))).toBe(1);
      const output = JSON.parse(captured());
      expect(output.structural.errors[0].kind).toBe("schema_missing");
      expect(output.structural.errors[0].message).toContain("escapes");
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
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
  });
});
