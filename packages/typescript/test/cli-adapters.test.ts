/** TypeScript-only CLI adapter boundaries not owned by shared goldens. */
import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { main } from "../src/cli.js";

const REPO = resolve(import.meta.dir, "../../..");
const MOVIE_DOC = resolve(REPO, "examples/movie_page/spirited-away.md");
const argv = (...args: string[]) => ["node", "cli.js", ...args];

let stdout = "";
let stderr = "";
let originalStdout: typeof process.stdout.write;
let originalStderr: typeof process.stderr.write;

beforeEach(() => {
  stdout = "";
  stderr = "";
  originalStdout = process.stdout.write.bind(process.stdout);
  originalStderr = process.stderr.write.bind(process.stderr);
  process.stdout.write = ((chunk: string | Uint8Array) => {
    stdout += chunk.toString();
    return true;
  }) as typeof process.stdout.write;
  process.stderr.write = ((chunk: string | Uint8Array) => {
    stderr += chunk.toString();
    return true;
  }) as typeof process.stderr.write;
});

afterEach(() => {
  process.stdout.write = originalStdout;
  process.stderr.write = originalStderr;
});

describe("TypeScript CLI adapter boundaries", () => {
  test("loads URL-sensitive model paths and explains runtime support", async () => {
    const dir = mkdtempSync(join(tmpdir(), "softschema model #"));
    const modulePath = join(dir, "movie model #%.mjs");
    const fixtureUrl = new URL("./fixtures/movie-model.mjs", import.meta.url).href;
    writeFileSync(modulePath, `export { MoviePage } from ${JSON.stringify(fixtureUrl)};\n`);
    try {
      expect(await main(argv("validate", MOVIE_DOC, "--model", `${modulePath}:MoviePage`))).toBe(0);
      expect(await main(argv("validate", MOVIE_DOC, "--model", `${dir}/missing.ts:MoviePage`))).toBe(2);
      expect(stderr).toContain("Node model paths must name built JavaScript");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("rejects a document schema symlink escape", async () => {
    const root = mkdtempSync(join(tmpdir(), "softschema-schema-link-"));
    const docs = join(root, "docs");
    mkdirSync(docs);
    writeFileSync(join(root, "outside.schema.yaml"), "type: object\n");
    symlinkSync(join(root, "outside.schema.yaml"), join(docs, "linked.schema.yaml"));
    const doc = join(docs, "artifact.md");
    writeFileSync(
      doc,
      "---\nsoftschema:\n  contract: example:Linked/v1\n  schema: linked.schema.yaml\nvalue: {}\n---\n",
    );
    try {
      expect(await main(argv("validate", doc))).toBe(1);
      expect(JSON.parse(stdout).structural.errors[0].kind).toBe("schema_missing");
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
