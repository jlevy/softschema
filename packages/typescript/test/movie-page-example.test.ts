/** The public TypeScript example must compile and validate like the Python example. */

import { expect, test } from "bun:test";
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { parse as parseYaml } from "yaml";
import { buildCanonicalSchema } from "../src/compile.js";
import { canonicalJson } from "../src/settings.js";

const ROOT = resolve(import.meta.dir, "../../..");
const SCHEMA = resolve(ROOT, "examples/movie_page/movie-page.schema.yaml");
const ARTIFACT = resolve(ROOT, "examples/movie_page/spirited-away.md");

async function loadExample(): Promise<{
  MoviePage: import("zod").z.ZodType;
  validateMoviePage: (path: string) => { ok: boolean; output?: Record<string, unknown> };
  cleanup: () => void;
}> {
  const directory = mkdtempSync(join(tmpdir(), "softschema-example-"));
  const packageRoot = join(directory, "node_modules/softschema");
  const exampleRoot = join(directory, "example");
  mkdirSync(packageRoot, { recursive: true });
  mkdirSync(exampleRoot, { recursive: true });
  writeFileSync(
    join(packageRoot, "package.json"),
    JSON.stringify({
      name: "softschema",
      type: "module",
      exports: { "./core": "./src/core/index.ts", "./node": "./src/node.ts" },
    }),
  );
  symlinkSync(resolve(ROOT, "packages/typescript/src"), join(packageRoot, "src"), "dir");
  symlinkSync(
    resolve(ROOT, "packages/typescript/node_modules/zod"),
    join(directory, "node_modules/zod"),
    "dir",
  );
  for (const name of ["model.ts", "host_integration.ts", "movie-page.schema.yaml"]) {
    copyFileSync(resolve(ROOT, "examples/movie_page", name), join(exampleRoot, name));
  }
  const model = await import(pathToFileURL(join(exampleRoot, "model.ts")).href);
  const host = await import(pathToFileURL(join(exampleRoot, "host_integration.ts")).href);
  return {
    MoviePage: model.MoviePage as import("zod").z.ZodType,
    validateMoviePage: host.validateMoviePage as (path: string) => {
      ok: boolean;
      output?: Record<string, unknown>;
    },
    cleanup: () => rmSync(directory, { recursive: true, force: true }),
  };
}

test("paired Zod model compiles to the committed movie schema", async () => {
  const { MoviePage, cleanup } = await loadExample();
  try {
    const compiled = buildCanonicalSchema(MoviePage, "example.movies:MoviePage/v1");
    const committed = parseYaml(readFileSync(SCHEMA, "utf8")) as Record<string, unknown>;
    const actualWithoutHash = structuredClone(compiled.schema);
    const expectedWithoutHash = structuredClone(committed);
    delete (actualWithoutHash["x-softschema"] as Record<string, unknown>).schema_sha256;
    delete (expectedWithoutHash["x-softschema"] as Record<string, unknown>).schema_sha256;
    expect(actualWithoutHash).toEqual(expectedWithoutHash);
    expect(canonicalJson(compiled.schema)).toBe(canonicalJson(committed));
  } finally {
    cleanup();
  }
});

test("paired TypeScript host validates the public artifact", async () => {
  const { validateMoviePage, cleanup } = await loadExample();
  try {
    const result = validateMoviePage(ARTIFACT);
    expect(result.ok, JSON.stringify(result)).toBe(true);
    if (!result.ok) return;
    const output = result.output as {
      values: { title: string } | null;
      contract_id: string;
    };
    expect(output.values?.title).toBe("Spirited Away");
    expect(output.contract_id).toBe("example.movies:MoviePage/v1");
  } finally {
    cleanup();
  }
});
